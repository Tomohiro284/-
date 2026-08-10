#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WebUI を1コマンドでセットアップする。

docs/01-setup.md の手順3〜7を自動化する。壊れる条件（非ASCIIパス、Python
バージョン違い、容量不足）は実行前に検査し、該当したら何もせずに中止する。

  python install/setup.py --dir C:\\sd\\webui
  python install/setup.py --dir ~/sd/webui --variant forge --preset sd15
  python install/setup.py --dir C:\\sd\\webui --dry-run

このスクリプトはモデルをダウンロードしない（数GBあり、ライセンス選択が
必要なため）。完了後に表示される案内に従って配置し、license_audit.py で
監査すること。
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parent.parent

REPOS = {
    "a1111": "https://github.com/AUTOMATIC1111/stable-diffusion-webui.git",
    "forge": "https://github.com/lllyasviel/stable-diffusion-webui-forge.git",
}


def fail(msg: str, hint: str = "") -> None:
    print(f"\n[中止] {msg}", file=sys.stderr)
    if hint:
        for line in hint.splitlines():
            print(f"       {line}", file=sys.stderr)
    raise SystemExit(2)


def step(n: int, total: int, title: str) -> None:
    print(f"\n[{n}/{total}] {title}")


def preflight(target: Path) -> None:
    """壊れる条件を、何かを書き込む前に全部潰す。"""
    non_ascii = [c for c in str(target) if ord(c) > 127]
    if non_ascii:
        fail(
            f"インストール先に非ASCII文字が含まれています: {target}",
            f"問題の文字: {''.join(dict.fromkeys(non_ascii))}\n"
            "WebUI は日本語を含むパスで確実に壊れます。C:\\sd\\webui のような\n"
            "半角英数のみのパスを --dir に指定してください。",
        )
    if " " in str(target):
        print("  ! 警告: パスに空白が含まれます。一部の拡張機能が誤動作します。")

    if not shutil.which("git"):
        fail("git が見つかりません", "https://git-scm.com/downloads からインストールしてください。")

    parent = target if target.exists() else target.parent
    while not parent.exists() and parent != parent.parent:
        parent = parent.parent
    free_gb = shutil.disk_usage(parent).free / (1024**3)
    if free_gb < 20:
        fail(
            f"空き容量が不足しています（{free_gb:.1f}GB）",
            "WebUI 本体と依存関係で約10GB、モデル1つで約6.5GB使います。\n"
            "20GB 以上空けてから再実行してください。",
        )
    print(f"  OK  パス: {target}")
    print(f"  OK  空き容量: {free_gb:.1f}GB")


def check_python(explicit: str | None) -> str:
    """WebUI を動かす Python 3.10 を特定する。実行中の Python とは別でよい。"""
    candidates = [explicit] if explicit else ["python3.10", "python3.10.exe"]
    for cmd in candidates:
        path = shutil.which(cmd) if cmd else None
        if not path:
            continue
        try:
            out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=15)
        except (OSError, subprocess.TimeoutExpired):
            continue
        ver = (out.stdout or out.stderr).strip()
        if "3.10." in ver:
            print(f"  OK  {ver} — {path}")
            return path
        print(f"  !   {ver} は 3.10.x ではありません — {path}")

    if explicit:
        fail(f"指定された Python が 3.10.x ではありません: {explicit}")

    print("  !   Python 3.10 が見つかりませんでした。")
    print("      WebUI の依存関係は 3.10.x 前提です。3.11 以降では torch の")
    print("      解決に失敗します。https://www.python.org/downloads/release/python-31011/")
    print("      から導入し、起動スクリプト内の PYTHON= を書き換えてください。")
    return ""


def clone(target: Path, url: str, dry_run: bool) -> None:
    if (target / "webui.py").exists():
        print(f"  OK  既にインストール済み: {target}")
        return
    if target.exists() and any(target.iterdir()):
        fail(f"{target} は空ではありませんが WebUI でもありません",
             "別のディレクトリを指定するか、中身を退避してください。")
    print(f"  clone {url}")
    if dry_run:
        print("      (dry-run: 実行しません)")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(["git", "clone", "--depth", "1", url, str(target)])
    if result.returncode != 0:
        fail("clone に失敗しました", "ネットワーク接続とプロキシ設定を確認してください。")


def install_launcher(target: Path, dry_run: bool) -> None:
    name = "webui-user.bat" if os.name == "nt" else "webui-user.sh"
    src = KIT_ROOT / "install" / name
    dest = target / name
    if not src.exists():
        fail(f"起動スクリプトが見つかりません: {src}")

    if dest.exists():
        backup = dest.with_suffix(dest.suffix + ".orig")
        if not backup.exists():
            print(f"  既存の {name} を {backup.name} として退避")
            if not dry_run:
                shutil.copy2(dest, backup)
    print(f"  配置 {dest}")
    if not dry_run:
        shutil.copy2(src, dest)
        if os.name != "nt":
            dest.chmod(0o755)


def apply_settings(target: Path, preset: str, dry_run: bool) -> None:
    cmd = [sys.executable, str(KIT_ROOT / "tools" / "apply_config.py"),
           "--webui-dir", str(target), "--preset", preset]
    if dry_run:
        cmd.append("--dry-run")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        fail("設定の適用に失敗しました")


def run_doctor(target: Path, py310: str) -> int:
    # WebUI が実際に使う Python で検査する。このスクリプト自身の Python とは
    # 別物なので、ここを取り違えるとバージョン判定が無意味になる。
    interpreter = py310 or sys.executable
    env = dict(os.environ, PYTHONUTF8="1")
    result = subprocess.run([interpreter, str(KIT_ROOT / "tools" / "doctor.py"),
                             "--webui-dir", str(target)], env=env)
    return result.returncode


def next_steps(target: Path, py310: str) -> None:
    launcher = "webui-user.bat" if os.name == "nt" else "./webui.sh"
    print("\n" + "=" * 66)
    print(" セットアップ完了。残りは手動です")
    print("=" * 66)
    print("\n1. モデルを配置する（このスクリプトはDLしません）")
    print(f"   {target / 'models' / 'Stable-diffusion'}")
    print("     stabilityai/stable-diffusion-xl-base-1.0 → sd_xl_base_1.0.safetensors")
    print(f"   {target / 'models' / 'VAE'}")
    print("     madebyollin/sdxl-vae-fp16-fix → sdxl_vae.safetensors")
    print("   ライセンスの詳細は models/allowlist.md（Tier A のみ使うこと）")

    print("\n2. 配置したモデルを監査する")
    print(f'   python tools/license_audit.py scan "{target / "models"}"')

    if not py310:
        print("\n3. Python 3.10 を導入し、起動スクリプトの PYTHON= を書き換える")
        print(f"   {target / ('webui-user.bat' if os.name == 'nt' else 'webui-user.sh')}")
    else:
        print(f"\n3. 起動スクリプト内の PYTHON= が {py310} を指しているか確認する")

    print("\n4. GPUに合わせて起動オプションを選ぶ（既定は [A] RTX 20/30/40/50 系）")
    print("   GTX 1650/1660 の場合は [B] を選ばないと黒画像・ノイズになります")

    print(f"\n5. 起動する: {launcher}")
    print("\n6. 起動後、シードの再現性を検証する")
    print("   python tools/verify_seed.py")


def main() -> int:
    parser = argparse.ArgumentParser(description="WebUI を1コマンドでセットアップする")
    parser.add_argument("--dir", required=True, help="インストール先（半角英数のみ）")
    parser.add_argument("--variant", choices=sorted(REPOS), default="a1111",
                        help="a1111=本家 / forge=高速版（既定: a1111）")
    parser.add_argument("--preset", default="sdxl", help="サンプラー設定 (sdxl / sd15 / flux-schnell)")
    parser.add_argument("--python", help="Python 3.10 の実行ファイルパス")
    parser.add_argument("--dry-run", action="store_true", help="何も書き込まずに手順だけ確認する")
    args = parser.parse_args()

    target = Path(args.dir).expanduser().resolve()
    total = 5

    print("=" * 66)
    print(f" WebUI セットアップ（{args.variant} / preset={args.preset}）")
    print("=" * 66)
    if args.dry_run:
        print(" dry-run: 書き込みは行いません")

    step(1, total, "事前チェック")
    preflight(target)

    step(2, total, "Python 3.10 の確認")
    py310 = check_python(args.python)

    step(3, total, "WebUI の取得")
    clone(target, REPOS[args.variant], args.dry_run)

    step(4, total, "起動スクリプトと推奨設定の適用")
    install_launcher(target, args.dry_run)
    if target.exists():
        apply_settings(target, args.preset, args.dry_run)
    else:
        # dry-run で clone を省いた場合、適用先がまだ存在しない
        print(f"  (適用先が未作成のためスキップ: preset={args.preset})")

    step(5, total, "セルフチェック")
    if args.dry_run:
        print("  (dry-run: 省略)")
    else:
        run_doctor(target, py310)

    next_steps(target, py310)
    return 0


if __name__ == "__main__":
    sys.exit(main())
