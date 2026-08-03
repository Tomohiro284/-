#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""config/ の設定を WebUI に安全に適用する。

既存の config.json / ui-config.json を丸ごと上書きすると、モデルのパスなど
環境固有の設定まで消えてしまうため、キー単位でマージする。適用前に必ず
バックアップを取る。

  python tools/apply_config.py --webui-dir "C:\\sd\\webui"
  python tools/apply_config.py --webui-dir ~/stable-diffusion-webui --dry-run
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parent.parent
PAIRS = [
    ("a1111-config.json", "config.json"),
    ("a1111-ui-config.json", "ui-config.json"),
]


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"  ! {path} が壊れています: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def apply(src: Path, dest: Path, dry_run: bool) -> int:
    desired = {k: v for k, v in _load(src).items() if not k.startswith("_")}
    current = _load(dest)

    changes = {k: v for k, v in desired.items() if current.get(k) != v}
    if not changes:
        print(f"  {dest.name}: 変更なし（{len(desired)} 項目すべて適用済み）")
        return 0

    print(f"  {dest.name}: {len(changes)} 項目を変更")
    for k, v in sorted(changes.items()):
        before = current.get(k, "(未設定)")
        print(f"    {k}: {before!r} → {v!r}")

    if dry_run:
        return len(changes)

    if dest.exists():
        backup = dest.with_name(f"{dest.stem}.bak-{datetime.now():%Y%m%d-%H%M%S}{dest.suffix}")
        shutil.copy2(dest, backup)
        print(f"    バックアップ: {backup.name}")

    current.update(changes)
    dest.write_text(json.dumps(current, ensure_ascii=False, indent=4), encoding="utf-8")
    return len(changes)


def main() -> int:
    parser = argparse.ArgumentParser(description="推奨設定を WebUI に適用する")
    parser.add_argument("--webui-dir", required=True, help="WebUI のインストールディレクトリ")
    parser.add_argument("--dry-run", action="store_true", help="変更内容を表示するだけで書き込まない")
    args = parser.parse_args()

    webui = Path(args.webui_dir).expanduser().resolve()
    if not webui.exists():
        print(f"ディレクトリがありません: {webui}", file=sys.stderr)
        return 2

    print(f"適用先: {webui}")
    if args.dry_run:
        print("(dry-run: 書き込みは行いません)")

    total = 0
    for src_name, dest_name in PAIRS:
        src = KIT_ROOT / "config" / src_name
        if not src.exists():
            print(f"  ! 設定ファイルがありません: {src}", file=sys.stderr)
            continue
        total += apply(src, webui / dest_name, args.dry_run)

    print(f"\n合計 {total} 項目")
    if total and not args.dry_run:
        print("WebUI を再起動すると反映されます。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
