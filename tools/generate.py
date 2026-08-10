#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""レシピの固定パラメータで画像を生成する。

config/recipes.json のパラメータをそのまま WebUI の API に投げる。seed が
固定してあるので、同じモデル・同じVAEなら何度実行しても同じ画像が出る。

前提: WebUI を --api 付きで起動しておくこと。

  python tools/generate.py --list
  python tools/generate.py portrait-sdxl
  python tools/generate.py --all --outdir ./outputs
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parent.parent
RECIPES_FILE = KIT_ROOT / "config" / "recipes.json"

# レシピ側で指定できるキー。ここに無いものは API に渡さない。
PASSTHROUGH = {
    "prompt", "seed", "steps", "cfg_scale", "width", "height",
    "sampler_name", "scheduler", "enable_hr", "hr_scale", "hr_upscaler",
    "hr_second_pass_steps", "denoising_strength",
}


def load_recipes() -> tuple[dict, str]:
    if not RECIPES_FILE.exists():
        print(f"レシピが見つかりません: {RECIPES_FILE}", file=sys.stderr)
        raise SystemExit(2)
    data = json.loads(RECIPES_FILE.read_text(encoding="utf-8"))
    return data.get("recipes", {}), data.get("_negative_common", "")


def build_payload(recipe: dict, negative: str) -> dict:
    payload = {k: v for k, v in recipe.items() if k in PASSTHROUGH}
    payload["negative_prompt"] = negative
    payload.setdefault("batch_size", 1)
    payload.setdefault("n_iter", 1)
    return payload


def post(url: str, payload: dict, timeout: int) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def generate(base_url: str, name: str, recipe: dict, negative: str,
             outdir: Path, timeout: int) -> bool:
    payload = build_payload(recipe, negative)
    url = f"{base_url.rstrip('/')}/sdapi/v1/txt2img"

    print(f"\n▶ {name} — {recipe.get('description', '')}")
    print(f"  model={recipe.get('base_model', '?')}  seed={payload['seed']}  "
          f"{payload['sampler_name']}/{payload.get('scheduler', '-')}  "
          f"steps={payload['steps']}  cfg={payload['cfg_scale']}  "
          f"{payload['width']}x{payload['height']}"
          + ("  +Hires" if payload.get("enable_hr") else ""))

    try:
        result = post(url, payload, timeout)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:300]
        if exc.code == 422 and "scheduler" in payload:
            # 古い WebUI は scheduler フィールドを持たず、サンプラー名に含める
            print("  （scheduler 非対応のため、サンプラー名に含めて再試行）")
            payload["sampler_name"] = f"{payload['sampler_name']} {payload.pop('scheduler')}"
            try:
                result = post(url, payload, timeout)
            except urllib.error.HTTPError as exc2:
                print(f"  × 失敗 HTTP {exc2.code}: {exc2.read().decode('utf-8', 'replace')[:300]}",
                      file=sys.stderr)
                return False
        else:
            print(f"  × 失敗 HTTP {exc.code}: {body}", file=sys.stderr)
            return False
    except urllib.error.URLError as exc:
        print(f"  × 接続できません: {exc}", file=sys.stderr)
        return False

    images = result.get("images") or []
    if not images:
        print("  × 画像が返りませんでした", file=sys.stderr)
        return False

    info = json.loads(result.get("info", "{}"))
    used_seed = info.get("seed", payload["seed"])

    outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = outdir / f"{name}_seed{used_seed}_{stamp}.png"
    path.write_bytes(base64.b64decode(images[0]))

    print(f"  ○ 保存: {path}")
    if used_seed != payload["seed"]:
        print(f"  ! 要求 seed={payload['seed']} に対し、実際は {used_seed} が使われました。")
    return True


def main() -> int:
    recipes, negative = load_recipes()

    parser = argparse.ArgumentParser(description="レシピの固定パラメータで画像を生成する")
    parser.add_argument("recipe", nargs="?", choices=sorted(recipes), help="実行するレシピ名")
    parser.add_argument("--all", action="store_true", help="全レシピを実行する")
    parser.add_argument("--list", action="store_true", help="レシピ一覧を表示する")
    parser.add_argument("--url", default="http://127.0.0.1:7860", help="WebUI の URL")
    parser.add_argument("--outdir", default=str(KIT_ROOT / "outputs"), help="保存先")
    parser.add_argument("--timeout", type=int, default=900, help="1枚あたりの待ち時間(秒)")
    args = parser.parse_args()

    if args.list or not (args.recipe or args.all):
        print("利用可能なレシピ:\n")
        for name, r in sorted(recipes.items()):
            print(f"  {name}")
            print(f"      {r.get('description', '')}")
            print(f"      model={r.get('base_model')}  seed={r.get('seed')}  "
                  f"steps={r.get('steps')}  cfg={r.get('cfg_scale')}  "
                  f"{r.get('width')}x{r.get('height')}\n")
        print("実行: python tools/generate.py <レシピ名>")
        return 0

    targets = sorted(recipes) if args.all else [args.recipe]
    outdir = Path(args.outdir).expanduser().resolve()

    print(f"接続先: {args.url}")
    ok = sum(generate(args.url, n, recipes[n], negative, outdir, args.timeout) for n in targets)

    print(f"\n{'-' * 60}")
    print(f" 成功 {ok} / {len(targets)}")
    if ok < len(targets):
        print(" WebUI が --api 付きで起動しているか、モデルが読み込まれているか確認してください。")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
