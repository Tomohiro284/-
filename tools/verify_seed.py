#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""シードの再現性を実測で検証する。

「決定的な設定にした」と主張するだけでは意味がないので、実際に WebUI の API を
叩いて確かめる。同じシードで2回生成し、結果が1ピクセルでも違えば不合格。

検証内容:
  1. 同一シード×2回        → 完全一致すること（再現性）
  2. 異なるシード          → 一致しないこと（テストが素通りしていないことの確認）
  3. バッチ内の位置ずれ    → batch_size=2 の1枚目が単発生成と一致すること

前提: WebUI を --api 付きで起動しておくこと（install/ の起動スクリプトは既定で有効）。

  python tools/verify_seed.py
  python tools/verify_seed.py --url http://127.0.0.1:7860 --steps 20
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import sys
import urllib.error
import urllib.request

DEFAULT_PROMPT = "a photograph of a red apple on a wooden table, natural light"


def _post(url: str, payload: dict, timeout: int) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def generate(base_url: str, payload: dict, timeout: int) -> tuple[list[str], dict]:
    """txt2img を叩いて画像(base64)のリストと info を返す。

    scheduler フィールドは新しめの WebUI にしかないため、422 が返ったら外して再試行する。
    """
    url = f"{base_url.rstrip('/')}/sdapi/v1/txt2img"
    try:
        result = _post(url, payload, timeout)
    except urllib.error.HTTPError as exc:
        if exc.code == 422 and "scheduler" in payload:
            payload = {k: v for k, v in payload.items() if k != "scheduler"}
            print("  （この WebUI は scheduler フィールド非対応のため、サンプラー名に含めて再試行）")
            payload["sampler_name"] = f"{payload['sampler_name']} Karras"
            result = _post(url, payload, timeout)
        else:
            raise

    info = json.loads(result.get("info", "{}"))
    return result.get("images", []), info


def fingerprint(b64: str) -> tuple[str, str]:
    """画像の指紋を返す (ピクセル基準, ファイル基準)。

    PNG にはパラメータ文字列が埋め込まれるため、ファイル全体のハッシュだけでは
    「メタデータだけ違う」のか「絵が違う」のか区別できない。Pillow があれば
    ピクセルデータそのものを比較する。
    """
    raw = base64.b64decode(b64)
    file_hash = hashlib.sha256(raw).hexdigest()[:16]
    try:
        from PIL import Image  # noqa: PLC0415

        with Image.open(io.BytesIO(raw)) as img:
            pixel_hash = hashlib.sha256(img.convert("RGB").tobytes()).hexdigest()[:16]
    except ImportError:
        pixel_hash = ""
    return pixel_hash, file_hash


def _describe(b64: str) -> str:
    px, fh = fingerprint(b64)
    return f"pixel={px or '(Pillow未導入)'} file={fh}"


def main() -> int:
    parser = argparse.ArgumentParser(description="シードの再現性を実測で検証する")
    parser.add_argument("--url", default="http://127.0.0.1:7860", help="WebUI の URL")
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--cfg", type=float, default=5.0)
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--sampler", default="DPM++ 2M")
    parser.add_argument("--scheduler", default="Karras")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--timeout", type=int, default=600, help="1回あたりの生成待ち時間(秒)")
    parser.add_argument("--skip-batch", action="store_true", help="バッチ整合性テストを省略する")
    args = parser.parse_args()

    base = {
        "prompt": args.prompt,
        "negative_prompt": "",
        "steps": args.steps,
        "cfg_scale": args.cfg,
        "width": args.width,
        "height": args.height,
        "sampler_name": args.sampler,
        "scheduler": args.scheduler,
        "seed": args.seed,
        "batch_size": 1,
        "n_iter": 1,
    }

    print("=" * 66)
    print(" シード再現性の検証")
    print("=" * 66)
    print(f" 接続先   : {args.url}")
    print(f" サンプラー: {args.sampler} / {args.scheduler}  steps={args.steps} cfg={args.cfg}")
    print(f" シード   : {args.seed}")
    print(f" サイズ   : {args.width}x{args.height}")
    print()

    try:
        print("[1/3] 1回目を生成中 …", flush=True)
        img_a, info_a = generate(args.url, dict(base), args.timeout)
        print("[2/3] 2回目を生成中（同一シード） …", flush=True)
        img_b, _ = generate(args.url, dict(base), args.timeout)
        print("[3/3] 3回目を生成中（異なるシード） …", flush=True)
        img_c, _ = generate(args.url, dict(base, seed=args.seed + 1), args.timeout)
    except urllib.error.URLError as exc:
        print(f"\n接続できません: {exc}", file=sys.stderr)
        print("WebUI を --api 付きで起動しているか確認してください。", file=sys.stderr)
        return 2
    except urllib.error.HTTPError as exc:
        print(f"\nAPI エラー HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:500]}", file=sys.stderr)
        return 2

    if not (img_a and img_b and img_c):
        print("画像が返りませんでした。", file=sys.stderr)
        return 2

    img_batch = None
    if not args.skip_batch:
        print("[追加] バッチ整合性を確認中（batch_size=2） …", flush=True)
        try:
            imgs, _ = generate(args.url, dict(base, batch_size=2), args.timeout)
            img_batch = imgs[0] if imgs else None
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            print(f"  （バッチテストはスキップ: {exc}）")

    print()
    print(f" 1回目 : {_describe(img_a[0])}")
    print(f" 2回目 : {_describe(img_b[0])}")
    print(f" 別シード: {_describe(img_c[0])}")
    if img_batch:
        print(f" バッチ : {_describe(img_batch)}")

    used_seed = info_a.get("seed")
    if used_seed is not None and used_seed != args.seed:
        print(f"\n 注意: 要求シード {args.seed} に対し、実際に使われたシードは {used_seed} でした。")

    print()
    print("-" * 66)
    failures = 0

    same = fingerprint(img_a[0]) == fingerprint(img_b[0])
    print(f"{'合格' if same else '不合格'}  再現性: 同一シードで完全に同じ画像になる")
    if not same:
        failures += 1
        print("      → docs/02-troubleshooting.md の 3-3 を参照。"
              "--xformers を外し、randn_source=CPU を確認してください。")

    differs = fingerprint(img_a[0]) != fingerprint(img_c[0])
    print(f"{'合格' if differs else '不合格'}  健全性: 異なるシードでは異なる画像になる")
    if not differs:
        failures += 1
        print("      → シードが反映されていません。設定を確認してください。")

    if img_batch:
        batch_ok = fingerprint(img_a[0]) == fingerprint(img_batch)
        print(f"{'合格' if batch_ok else '不合格'}  バッチ整合性: batch_size を変えても結果が変わらない")
        if not batch_ok:
            failures += 1
            print("      → no_dpmpp_sde_batch_determinism を有効にするか、"
                  "SDE系以外のサンプラーを使ってください。")

    if not fingerprint(img_a[0])[0]:
        print("\n 補足: Pillow が未導入のためファイル全体のハッシュで比較しました。"
              "\n       PNG メタデータの差も検出してしまうため、判定は厳しめに出ます。"
              "\n       正確に比較するには pip install Pillow を実行してください。")

    print("-" * 66)
    if failures:
        print(f" {failures} 件不合格。設定が決定的になっていません。")
        return 1
    print(" すべて合格。シードは正確に再現されます。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
