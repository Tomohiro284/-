#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""起動前セルフチェック。

ノイズ（黒画像 / NaN）・文字化け・環境由来のバグを、生成を始める前に検出する。

終了コード:
  0 = 問題なし
  1 = 警告あり（起動は可能）
  2 = 致命的（このまま起動しても壊れた画像しか出ない）
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

OK, WARN, FATAL = "OK", "WARN", "FATAL"
_results: list[tuple[str, str, str]] = []


def report(level: str, title: str, detail: str = "") -> None:
    _results.append((level, title, detail))


# --------------------------------------------------------------------------
# 各チェック
# --------------------------------------------------------------------------
def check_python() -> None:
    major, minor = sys.version_info[:2]
    ver = f"{major}.{minor}.{sys.version_info[2]}"
    if (major, minor) == (3, 10):
        report(OK, f"Python {ver}")
    elif (major, minor) < (3, 10):
        report(FATAL, f"Python {ver} は古すぎます", "3.10.6〜3.10.11 を使ってください。")
    else:
        report(
            WARN,
            f"Python {ver} は非推奨です",
            "AUTOMATIC1111 の依存関係は 3.10.x 前提です。3.11 以降は "
            "torch / torchvision の解決に失敗したり、拡張機能が動かないことがあります。",
        )


def check_path_ascii(*paths: Path) -> None:
    """非ASCIIパスは A1111 の既知のクラッシュ要因（キャッシュ・ログ書き込みで落ちる）。"""
    for p in paths:
        if p is None:
            continue
        s = str(p)
        non_ascii = [c for c in s if ord(c) > 127]
        if non_ascii:
            sample = "".join(dict.fromkeys(non_ascii))[:12]
            report(
                FATAL,
                "パスに非ASCII文字が含まれています",
                f"{s}\n  問題の文字: {sample}\n"
                "  → C:\\sd\\ など半角英数のみのパスに移動してください。"
                "（ユーザー名が日本語のときの Windows で頻発）",
            )
        elif " " in s:
            report(WARN, "パスに空白が含まれています", f"{s}\n  → 一部の拡張機能がパスを誤解釈します。")
        else:
            report(OK, f"パスは安全: {s}")


def check_encoding() -> None:
    enc = (sys.stdout.encoding or "").lower().replace("-", "")
    fs_enc = sys.getfilesystemencoding().lower().replace("-", "")
    if enc.startswith("utf8") and fs_enc.startswith("utf8"):
        report(OK, f"文字コード UTF-8 (stdout={sys.stdout.encoding}, fs={sys.getfilesystemencoding()})")
    else:
        report(
            FATAL,
            f"文字コードが UTF-8 ではありません (stdout={sys.stdout.encoding}, fs={sys.getfilesystemencoding()})",
            "この状態だと日本語プロンプト・ログ・ファイル名が化けます。\n"
            "  Windows: 起動バッチ先頭に  chcp 65001 と set PYTHONUTF8=1\n"
            "  Linux/macOS: export PYTHONUTF8=1  export LANG=C.UTF-8",
        )

    if os.environ.get("PYTHONUTF8") != "1":
        report(WARN, "環境変数 PYTHONUTF8 が 1 ではありません", "UTF-8モードを明示すると化けを防げます。")


def check_torch() -> None:
    try:
        import torch  # noqa: PLC0415
    except ImportError:
        report(WARN, "torch 未インストール", "WebUI の初回起動時に自動導入されます（このチェックはスキップ）。")
        return

    report(OK, f"torch {torch.__version__}")

    if torch.cuda.is_available():
        name = torch.cuda.get_device_name(0)
        cap = torch.cuda.get_device_capability(0)
        vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        report(OK, f"GPU: {name} (compute {cap[0]}.{cap[1]}, VRAM {vram:.1f}GB)")
        _check_fp16_sanity(torch)
        _advise_vram(vram)
    elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        report(OK, "GPU: Apple Silicon (MPS)")
        report(WARN, "MPS は fp16 が不安定です", "--no-half-vae --upcast-sampling を必ず付けてください。")
    else:
        report(
            WARN,
            "GPU が検出されません（CPU実行）",
            "1枚あたり数分〜十数分かかります。起動オプション [E]/[G] を選んでください。",
        )


def _check_fp16_sanity(torch) -> None:
    """GTX 16xx 等で fp16 演算が NaN になる個体を実測で検出する。

    これを見逃すと『真っ黒 or 全面ノイズの画像しか出ない』という典型症状になる。
    """
    try:
        a = torch.randn(256, 256, device="cuda", dtype=torch.float16)
        b = torch.randn(256, 256, device="cuda", dtype=torch.float16)
        c = a @ b
        if torch.isnan(c).any() or torch.isinf(c).any():
            report(
                FATAL,
                "fp16 演算が NaN/Inf を返しました",
                "このGPUでは半精度が壊れています。→ 起動オプション [B]\n"
                "  --precision full --no-half --no-half-vae  を使ってください。",
            )
        else:
            report(OK, "fp16 演算の健全性チェック 合格（黒画像・全面ノイズのリスクなし）")
    except Exception as exc:  # noqa: BLE001
        report(WARN, "fp16 チェックを実行できませんでした", str(exc))


def _advise_vram(vram_gb: float) -> None:
    if vram_gb < 4.5:
        report(WARN, f"VRAM {vram_gb:.1f}GB は不足気味", "起動オプション [D] --lowvram を選んでください。")
    elif vram_gb < 6.5:
        report(WARN, f"VRAM {vram_gb:.1f}GB", "起動オプション [C] --medvram を選んでください。SDXL 1024px は厳しめです。")
    elif vram_gb < 10:
        report(OK, f"VRAM {vram_gb:.1f}GB — SDXL 1024px が動作可能")
    else:
        report(OK, f"VRAM {vram_gb:.1f}GB — 余裕あり")


def check_disk(webui_dir: Path) -> None:
    target = webui_dir if webui_dir.exists() else Path.cwd()
    free_gb = shutil.disk_usage(target).free / (1024**3)
    if free_gb < 10:
        report(FATAL, f"空き容量 {free_gb:.1f}GB", "モデル書き込み中に破損します。20GB 以上空けてください。")
    elif free_gb < 25:
        report(WARN, f"空き容量 {free_gb:.1f}GB", "SDXL系は1モデル約6.5GB。余裕を見て 25GB 以上を推奨。")
    else:
        report(OK, f"空き容量 {free_gb:.1f}GB")


def check_models(webui_dir: Path) -> None:
    ckpt_dir = webui_dir / "models" / "Stable-diffusion"
    vae_dir = webui_dir / "models" / "VAE"

    if not ckpt_dir.exists():
        report(WARN, "checkpoint ディレクトリが見つかりません", f"{ckpt_dir}\n  → WebUI 未インストール、または --webui-dir の指定違い。")
        return

    ckpts = [p for p in ckpt_dir.rglob("*") if p.suffix in {".safetensors", ".ckpt"}]
    if not ckpts:
        report(FATAL, "checkpoint が1つもありません", f"{ckpt_dir} にモデルを置いてください（models/allowlist.md 参照）。")
    else:
        report(OK, f"checkpoint {len(ckpts)} 件")
        legacy = [p.name for p in ckpts if p.suffix == ".ckpt"]
        if legacy:
            report(
                WARN,
                f".ckpt 形式が {len(legacy)} 件あります",
                "任意コード実行のリスクがあります。.safetensors 版に置き換えてください: " + ", ".join(legacy[:3]),
            )

    vaes = [p for p in vae_dir.rglob("*") if p.suffix in {".safetensors", ".pt", ".ckpt"}] if vae_dir.exists() else []
    if not vaes:
        report(
            WARN,
            "外部 VAE が未配置",
            "モデル内蔵VAEで動きますが、色あせ・紫斑点・全面ノイズが出る場合は\n"
            "  SDXL: sdxl-vae-fp16-fix / SD1.5: vae-ft-mse-840000 を導入してください。",
        )
    else:
        report(OK, f"VAE {len(vaes)} 件")


def check_extensions(webui_dir: Path) -> None:
    ext_dir = webui_dir / "extensions"
    if not ext_dir.exists():
        return
    exts = [p.name for p in ext_dir.iterdir() if p.is_dir() and not p.name.startswith(".")]
    if len(exts) == 0:
        report(OK, "拡張機能なし（最も安定）")
    elif len(exts) <= 3:
        report(OK, f"拡張機能 {len(exts)} 件: {', '.join(exts)}")
    else:
        report(
            WARN,
            f"拡張機能が {len(exts)} 件あります",
            "拡張機能どうしの依存衝突は WebUI が起動しなくなる最頻原因です。\n"
            "  不具合が出たら --disable-extra-extensions で切り分けてください。\n"
            "  " + ", ".join(exts),
        )


def check_filename_pattern(webui_dir: Path) -> None:
    """出力ファイル名にプロンプトを埋めると、日本語プロンプトでファイル名が壊れる。"""
    cfg = webui_dir / "config.json"
    if not cfg.exists():
        return
    try:
        import json  # noqa: PLC0415

        data = json.loads(cfg.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        report(WARN, "config.json を読めませんでした", str(cfg))
        return

    pattern = data.get("samples_filename_pattern", "")
    if "[prompt" in pattern:
        report(
            WARN,
            "出力ファイル名にプロンプトが含まれる設定です",
            f"pattern={pattern!r}\n  → 日本語プロンプトでファイル名が化けます。"
            "[seed]-[model_name] を推奨（config/a1111-config.json 参照）。",
        )
    if data.get("live_previews_enable") and data.get("show_progress_type") in {"Approx NN", "Approx cheap"}:
        report(
            WARN,
            "生成中プレビューが近似モードです",
            "途中経過がザラついて見えますが、これは不具合ではありません。"
            "紛らわしい場合は show_progress_type を 'Full' にするか、プレビューを無効化してください。",
        )


# --------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Stable Diffusion 起動前セルフチェック")
    parser.add_argument("--webui-dir", default=".", help="WebUI のインストールディレクトリ")
    args = parser.parse_args()

    webui_dir = Path(args.webui_dir).expanduser().resolve()

    print("=" * 66)
    print(" Stable Diffusion 起動前セルフチェック")
    print("=" * 66)

    check_python()
    check_encoding()
    check_path_ascii(webui_dir)
    check_torch()
    check_disk(webui_dir)
    check_models(webui_dir)
    check_extensions(webui_dir)
    check_filename_pattern(webui_dir)

    icon = {OK: "  OK ", WARN: " 警告", FATAL: " 致命"}
    for level, title, detail in _results:
        print(f"[{icon[level]}] {title}")
        if detail:
            for line in detail.splitlines():
                print(f"         {line}")

    fatals = sum(1 for lv, _, _ in _results if lv == FATAL)
    warns = sum(1 for lv, _, _ in _results if lv == WARN)

    print("-" * 66)
    print(f" 致命 {fatals} 件 / 警告 {warns} 件")
    if fatals:
        print(" → 致命的な問題があります。修正するまで、まともな画像は生成できません。")
        return 2
    if warns:
        print(" → 起動は可能です。警告内容を確認してください。")
        return 1
    print(" → 問題なし。起動できます。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
