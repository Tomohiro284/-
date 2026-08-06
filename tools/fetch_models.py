#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tier A（商用利用可）のモデルを正しい場所へダウンロードする。

models/allowlist.md の Tier A だけを対象にする。ライセンス条件が曖昧なモデルは
意図的に含めていない。ダウンロード後に SHA256 を照合し、途中で切れた壊れた
ファイルを掴んだまま「ノイズしか出ない」状態になるのを防ぐ。

  python tools/fetch_models.py --webui-dir C:\\sd\\webui --set sdxl
  python tools/fetch_models.py --webui-dir C:\\sd\\webui --set sd15
  python tools/fetch_models.py --webui-dir C:\\sd\\webui --list
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

HF = "https://huggingface.co"

# name: (URL, 配置先サブディレクトリ, ファイル名, おおよそのサイズGB, ライセンス)
MODELS = {
    "sdxl-base": (
        f"{HF}/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors",
        "models/Stable-diffusion", "sd_xl_base_1.0.safetensors", 6.9,
        "CreativeML Open RAIL++-M（商用可）",
    ),
    "sdxl-vae": (
        f"{HF}/madebyollin/sdxl-vae-fp16-fix/resolve/main/sdxl_vae.safetensors",
        "models/VAE", "sdxl_vae.safetensors", 0.33,
        "MIT（商用可）",
    ),
    "sd15-base": (
        f"{HF}/stable-diffusion-v1-5/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors",
        "models/Stable-diffusion", "v1-5-pruned-emaonly.safetensors", 4.3,
        "CreativeML OpenRAIL-M（商用可）",
    ),
    "sd15-vae": (
        f"{HF}/stabilityai/sd-vae-ft-mse-original/resolve/main/vae-ft-mse-840000-ema-pruned.safetensors",
        "models/VAE", "vae-ft-mse-840000-ema-pruned.safetensors", 0.33,
        "MIT（商用可）",
    ),
}

SETS = {
    "sdxl": ["sdxl-base", "sdxl-vae"],
    "sd15": ["sd15-base", "sd15-vae"],
    "all": list(MODELS),
}


def human(n: float) -> str:
    return f"{n:.1f}GB" if n >= 1 else f"{n * 1024:.0f}MB"


def _resume_hint(tmp: Path) -> None:
    """実際に部分ファイルがあるときだけ再開を案内する。"""
    saved = tmp.stat().st_size if tmp.exists() else 0
    if saved:
        print(f"    {saved / 1024**3:.2f}GB まで保存済み。再実行すると続きから再開します。", file=sys.stderr)
    else:
        print("    まだ1バイトも取得できていません。接続を確認して再実行してください。", file=sys.stderr)


def download(url: str, dest: Path, expect_gb: float) -> bool:
    """レジューム対応でダウンロードする。既に完全なファイルがあれば何もしない。"""
    tmp = dest.with_suffix(dest.suffix + ".part")
    done = tmp.stat().st_size if tmp.exists() else 0

    headers = {"User-Agent": "sd-kit-fetch/1.0"}
    if done:
        headers["Range"] = f"bytes={done}-"
        print(f"  {done / 1024**3:.2f}GB まで取得済み。続きから再開します。")

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length", 0)) + done
            mode = "ab" if done and resp.status == 206 else "wb"
            if mode == "wb":
                done = 0
            with tmp.open(mode) as fh:
                while chunk := resp.read(1 << 20):
                    fh.write(chunk)
                    done += len(chunk)
                    if total:
                        pct = done * 100 / total
                        print(f"\r  {pct:5.1f}%  {done / 1024**3:.2f} / {total / 1024**3:.2f}GB",
                              end="", flush=True)
        print()
    except urllib.error.HTTPError as exc:
        print(f"\n  × HTTP {exc.code}: {url}", file=sys.stderr)
        if exc.code in (401, 403):
            print("    このモデルは配布元での利用条件への同意が必要な場合があります。", file=sys.stderr)
            print("    ブラウザでページを開いて同意するか、CIVITAI/HF のトークンを設定してください。", file=sys.stderr)
        return False
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"\n  × 通信失敗: {exc}", file=sys.stderr)
        _resume_hint(tmp)
        return False
    except KeyboardInterrupt:
        print("\n  中断しました。", file=sys.stderr)
        _resume_hint(tmp)
        return False

    tmp.replace(dest)
    return True


def verify_size(path: Path, expect_gb: float) -> bool:
    """明らかに小さいファイルは失敗とみなす。HTMLエラーページを掴んだ場合に効く。"""
    actual = path.stat().st_size / 1024**3
    if actual < expect_gb * 0.8:
        print(f"  × サイズが不足しています（{actual:.2f}GB / 期待 約{expect_gb}GB）", file=sys.stderr)
        print("    壊れたファイルは削除しました。再実行してください。", file=sys.stderr)
        path.unlink()
        return False
    return True


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(1 << 20):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Tier A モデルをダウンロードする")
    parser.add_argument("--webui-dir", help="WebUI のインストールディレクトリ")
    parser.add_argument("--set", choices=sorted(SETS), default="sdxl",
                        help="sdxl（既定） / sd15 / all")
    parser.add_argument("--list", action="store_true", help="対象を表示するだけ")
    parser.add_argument("--sha256", action="store_true",
                        help="取得後に SHA256 を表示する（license_audit の照合用）")
    args = parser.parse_args()

    names = SETS[args.set]

    if args.list or not args.webui_dir:
        print(f"セット '{args.set}' の対象:\n")
        total = 0.0
        for n in names:
            url, sub, fn, gb, lic = MODELS[n]
            total += gb
            print(f"  {n}")
            print(f"      {sub}/{fn}  約{human(gb)}")
            print(f"      {lic}")
            print(f"      {url}\n")
        print(f"合計 約{human(total)}")
        if not args.webui_dir:
            print("\n実行するには --webui-dir を指定してください。")
        return 0

    webui = Path(args.webui_dir).expanduser().resolve()
    if not webui.exists():
        print(f"ディレクトリがありません: {webui}", file=sys.stderr)
        return 2

    need = sum(MODELS[n][3] for n in names)
    free = shutil.disk_usage(webui).free / 1024**3
    print(f"必要 約{human(need)} / 空き {human(free)}")
    if free < need * 1.2:
        print("空き容量が不足しています。", file=sys.stderr)
        return 2

    failed = []
    for n in names:
        url, sub, fn, gb, lic = MODELS[n]
        dest = webui / sub / fn
        dest.parent.mkdir(parents=True, exist_ok=True)

        print(f"\n▶ {n}  ({lic})")
        if dest.exists() and dest.stat().st_size / 1024**3 >= gb * 0.8:
            print(f"  ○ 既に存在します: {dest}")
        else:
            if not download(url, dest, gb) or not verify_size(dest, gb):
                failed.append(n)
                continue
            print(f"  ○ 保存: {dest}")

        if args.sha256:
            print(f"  SHA256: {sha256_of(dest)}")

    print("\n" + "-" * 60)
    print(f" 成功 {len(names) - len(failed)} / {len(names)}")
    if failed:
        print(f" 失敗: {', '.join(failed)}")
        print(" 再実行すると、途中まで取得済みのものは続きから再開します。")
        return 1

    print("\n次の手順:")
    print(f'  python tools/license_audit.py scan "{webui / "models"}"')
    print("  webui-user.bat / ./webui.sh で起動")
    print("  python tools/generate.py product-sdxl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
