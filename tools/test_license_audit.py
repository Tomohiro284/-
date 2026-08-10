#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""license_audit の判定ロジックの単体テスト。

Civitai API をスタブに差し替えて実行するのでネットワーク不要。

  python tools/test_license_audit.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import license_audit as la  # noqa: E402

# 実 API のレスポンス形状を模したスタブ。
# allowCommercialUse は配列を返す版と単一文字列を返す版の両方が存在するため、両方を含める。
FAKE = {
    f"{la.API}/models/1": {
        "name": "OpenRAIL Model", "type": "Checkpoint",
        "allowCommercialUse": ["Image", "Rent", "Sell"],
        "allowNoCredit": True, "allowDerivatives": True, "allowDifferentLicense": True,
        "modelVersions": [{"baseModel": "SDXL 1.0"}],
    },
    f"{la.API}/models/2": {
        "name": "NonCommercial Model", "type": "Checkpoint",
        "allowCommercialUse": ["None"],
        "allowNoCredit": False, "allowDerivatives": False, "allowDifferentLicense": False,
        "modelVersions": [{"baseModel": "Flux.1 D"}],
    },
    f"{la.API}/models/3": {
        "name": "Image-only LoRA", "type": "LORA",
        "allowCommercialUse": "Image",          # 文字列形式
        "allowNoCredit": False, "allowDerivatives": True, "allowDifferentLicense": False,
        "modelVersions": [{"baseModel": "Pony"}],
    },
    f"{la.API}/models/4": {
        "name": "RentCivit only", "type": "LORA",
        "allowCommercialUse": ["RentCivit"],    # Civitai内でのみ有償利用可＝画像の商用利用は不可
        "allowNoCredit": True, "allowDerivatives": True, "allowDifferentLicense": True,
        "modelVersions": [{"baseModel": "SD 1.5"}],
    },
    f"{la.API}/models/5": {
        "name": "Missing field", "type": "Checkpoint",
        "modelVersions": [],                    # allowCommercialUse そのものが無い
    },
}

CASES = [
    # (policy, model_id, expected_status)
    ("standard", 1, "PASS"),
    ("standard", 2, "FAIL"),   # 商用不可
    ("standard", 3, "PASS"),   # 文字列形式でも解釈できる
    ("standard", 4, "FAIL"),   # Image が無い
    ("standard", 5, "FAIL"),   # フィールド欠落は不許可側に倒す
    ("strict", 1, "PASS"),
    ("strict", 2, "FAIL"),
    ("strict", 3, "FAIL"),     # Rent / Sell が不足
    ("strict", 4, "FAIL"),
    ("strict", 5, "FAIL"),
]


def main() -> int:
    la._request = lambda url, retries=4: FAKE.get(url)  # noqa: SLF001

    failures = 0
    for policy, model_id, expected in CASES:
        v = la.audit_model_id(model_id, la.POLICIES[policy])
        ok = v.status == expected
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  [{policy:<8}] id={model_id}  "
              f"{v.status:<7} (期待 {expected})  {v.name}")

    # 未登録IDは UNKNOWN（＝判定不能として人間に回す）であること
    v = la.audit_model_id(999, la.POLICIES["standard"])
    ok = v.status == "UNKNOWN"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  [未登録ID ] {v.status} (期待 UNKNOWN)")

    print("-" * 60)
    if failures:
        print(f"{failures} 件失敗")
        return 1
    print(f"全 {len(CASES) + 1} ケース合格")
    return 0


if __name__ == "__main__":
    sys.exit(main())
