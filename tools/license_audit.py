#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Checkpoint / LoRA のライセンス監査ツール。

Civitai の「緑チェック」は API の allowCommercialUse フィールドに対応する。
目視で1つずつ確認するとほぼ確実に見落とすので、機械判定する。

allowCommercialUse の値と、Civitai のモデルページ上の表示の対応:
    Image      … 生成した画像を販売してよい      （商用利用の最低ライン）
    Rent       … 有料サービス上でモデルを動かしてよい
    RentCivit  … Civitai の有料機能で使ってよい
    Sell       … モデル自体を販売してよい
    None       … 商用利用不可（＝赤バツ）

使い方:
  # 1) 手元の models フォルダを丸ごと監査（推奨）
  python tools/license_audit.py scan "C:\\sd\\webui\\models"

  # 2) ダウンロード前に個別確認
  python tools/license_audit.py check https://civitai.com/models/133005 4384

  # 3) CI / スクリプトから使う
  python tools/license_audit.py scan ./models --json report.json --quarantine
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

API = "https://civitai.com/api/v1"
MODEL_SUFFIXES = {".safetensors", ".ckpt", ".pt", ".bin"}

# 商用利用ポリシー。値は「合格に必要な許諾の集合」で、すべて満たす必要がある。
# ユーザー要件「緑チェックのみ」= standard 以上。
POLICIES = {
    "standard": {"Image"},                  # 生成画像の商用利用が可能であればよい
    "strict": {"Image", "Rent", "Sell"},    # 画像販売・サービス提供・再配布のすべてが可
}


# --------------------------------------------------------------------------
@dataclass
class Verdict:
    path: str
    name: str = "?"
    model_id: int | None = None
    version_name: str = ""
    base_model: str = ""
    model_type: str = ""
    allow_commercial: list[str] = field(default_factory=list)
    allow_no_credit: bool | None = None
    allow_derivatives: bool | None = None
    allow_different_license: bool | None = None
    status: str = "UNKNOWN"   # PASS / FAIL / UNKNOWN
    reason: str = ""

    @property
    def url(self) -> str:
        return f"https://civitai.com/models/{self.model_id}" if self.model_id else ""


# --------------------------------------------------------------------------
def _request(url: str, retries: int = 4) -> dict | None:
    """Civitai API を叩く。429/5xx は指数バックオフで再試行。"""
    headers = {"User-Agent": "sd-license-audit/1.0"}
    token = os.environ.get("CIVITAI_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    delay = 2.0
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            print(f"  ! HTTP {exc.code}: {url}", file=sys.stderr)
            return None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            print(f"  ! 通信失敗: {exc}", file=sys.stderr)
            return None
    return None


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest().upper()


def _normalize_commercial(raw) -> list[str]:
    """API は list を返す版と単一文字列を返す版がある。両方受ける。"""
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = [raw]
    return [str(v) for v in raw if str(v) and str(v) != "None"]


def _judge(v: Verdict, required: set[str]) -> None:
    granted = set(v.allow_commercial)
    if not granted:
        v.status, v.reason = "FAIL", "商用利用不可（赤バツ）"
    elif required <= granted:
        v.status = "PASS"
        v.reason = "商用利用可: " + ", ".join(sorted(granted))
    else:
        missing = ", ".join(sorted(required - granted))
        v.status = "FAIL"
        v.reason = f"許諾が不足（不足: {missing} / 付与: {', '.join(sorted(granted))}）"


# --------------------------------------------------------------------------
def audit_model_id(model_id: int, allowed: set[str], path: str = "") -> Verdict:
    v = Verdict(path=path or f"model:{model_id}", model_id=model_id)
    data = _request(f"{API}/models/{model_id}")
    if data is None:
        v.reason = "Civitai に該当モデルなし（削除済み / 非公開 / 通信失敗）"
        return v

    v.name = data.get("name", "?")
    v.model_type = data.get("type", "")
    v.allow_commercial = _normalize_commercial(data.get("allowCommercialUse"))
    v.allow_no_credit = data.get("allowNoCredit")
    v.allow_derivatives = data.get("allowDerivatives")
    v.allow_different_license = data.get("allowDifferentLicense")
    versions = data.get("modelVersions") or []
    if versions:
        v.base_model = versions[0].get("baseModel", "")
    _judge(v, allowed)
    return v


def audit_file(path: Path, allowed: set[str]) -> Verdict:
    v = Verdict(path=str(path), name=path.name)
    digest = sha256_file(path)

    ver = _request(f"{API}/model-versions/by-hash/{digest}")
    if ver is None:
        v.reason = (
            "Civitai で照合できません（自作 / HuggingFace由来 / マージ済み）。"
            "配布元のライセンスを手動で確認してください。"
        )
        return v

    v.model_id = ver.get("modelId")
    v.version_name = ver.get("name", "")
    v.base_model = ver.get("baseModel", "")
    if not v.model_id:
        v.reason = "modelId を取得できませんでした"
        return v

    full = audit_model_id(v.model_id, allowed, path=str(path))
    full.path = str(path)
    full.version_name = v.version_name
    full.base_model = v.base_model or full.base_model
    return full


# --------------------------------------------------------------------------
def cmd_scan(args: argparse.Namespace) -> int:
    allowed = POLICIES[args.policy]
    root = Path(args.directory).expanduser().resolve()
    if not root.exists():
        print(f"ディレクトリがありません: {root}", file=sys.stderr)
        return 2

    files = sorted(p for p in root.rglob("*") if p.suffix.lower() in MODEL_SUFFIXES and p.is_file())
    if not files:
        print(f"モデルファイルが見つかりません: {root}")
        return 0

    print(f"対象 {len(files)} 件 / ポリシー: {args.policy}\n")
    verdicts: list[Verdict] = []
    for i, path in enumerate(files, 1):
        size_mb = path.stat().st_size / (1024**2)
        print(f"[{i}/{len(files)}] {path.name} ({size_mb:.0f}MB) … ハッシュ計算中", flush=True)
        verdicts.append(audit_file(path, allowed))
        time.sleep(args.sleep)

    _print_report(verdicts)

    if args.json:
        Path(args.json).write_text(
            json.dumps([v.__dict__ | {"url": v.url} for v in verdicts], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nJSON を書き出しました: {args.json}")

    failed = [v for v in verdicts if v.status == "FAIL"]
    unknown = [v for v in verdicts if v.status == "UNKNOWN"]

    if args.quarantine and (failed or unknown):
        qdir = root / "_quarantine_license"
        qdir.mkdir(exist_ok=True)
        for v in failed + unknown:
            src = Path(v.path)
            if src.exists() and qdir not in src.parents:
                dest = qdir / src.name
                src.rename(dest)
                print(f"  隔離: {src.name} → {dest}")

    return 1 if failed else 0


def cmd_check(args: argparse.Namespace) -> int:
    allowed = POLICIES[args.policy]
    verdicts = []
    for token in args.targets:
        m = re.search(r"(?:civitai\.com/models/)?(\d+)", token)
        if not m:
            print(f"モデルIDを解釈できません: {token}", file=sys.stderr)
            continue
        verdicts.append(audit_model_id(int(m.group(1)), allowed))
        time.sleep(args.sleep)

    _print_report(verdicts)
    return 1 if any(v.status == "FAIL" for v in verdicts) else 0


def _print_report(verdicts: list[Verdict]) -> None:
    mark = {"PASS": "○ 商用可", "FAIL": "× 商用不可", "UNKNOWN": "△ 要確認"}
    print("\n" + "=" * 78)
    print(" ライセンス監査結果")
    print("=" * 78)
    for v in verdicts:
        print(f"{mark[v.status]}  {v.name}")
        if v.version_name:
            print(f"            version : {v.version_name}")
        if v.base_model:
            print(f"            base    : {v.base_model}")
        print(f"            判定    : {v.reason}")
        if v.status == "PASS":
            extras = []
            if v.allow_no_credit is False:
                extras.append("クレジット表記が必須")
            if v.allow_derivatives is False:
                extras.append("マージ・派生の作成不可")
            if v.allow_different_license is False:
                extras.append("派生物は同一ライセンスの継承が必要")
            if extras:
                print(f"            条件    : {' / '.join(extras)}")
        if v.url:
            print(f"            {v.url}")
        print()

    n_pass = sum(1 for v in verdicts if v.status == "PASS")
    n_fail = sum(1 for v in verdicts if v.status == "FAIL")
    n_unk = sum(1 for v in verdicts if v.status == "UNKNOWN")
    print("-" * 78)
    print(f" 商用可 {n_pass} / 商用不可 {n_fail} / 要確認 {n_unk}")
    if n_fail:
        print(" → 『商用不可』のモデルは models フォルダから外してください。")
    if n_unk:
        print(" → 『要確認』は Civitai 外のモデルです。配布元のライセンス条文を確認してください。")


def main() -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--policy", choices=sorted(POLICIES), default="standard",
                        help="standard=画像の商用利用が可能なら合格 / strict=販売・サービス提供まで可なら合格")
    common.add_argument("--sleep", type=float, default=0.5, help="APIリクエスト間隔(秒)")

    parser = argparse.ArgumentParser(description="Checkpoint / LoRA のライセンス監査")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", parents=[common],
                            help="ディレクトリ内のモデルをハッシュ照合で一括監査")
    p_scan.add_argument("directory")
    p_scan.add_argument("--json", help="結果をJSONで書き出す")
    p_scan.add_argument("--quarantine", action="store_true",
                        help="不合格・要確認のモデルを _quarantine_license/ に移動する")
    p_scan.set_defaults(func=cmd_scan)

    p_check = sub.add_parser("check", parents=[common], help="モデルURL / ID を指定して事前確認")
    p_check.add_argument("targets", nargs="+")
    p_check.set_defaults(func=cmd_check)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
