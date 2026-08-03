# 商用利用可モデル 許可リスト

**重要な前提**: 以下はライセンス文面が公開されていて条件が明確なものだけを挙げています。
ただし**ライセンスは配布者の判断でいつでも変更されます**。ダウンロード時点で必ず
`tools/license_audit.py` または配布元の LICENSE ファイル本文で再確認してください。
このファイルは「確認の出発点」であって、法的な保証ではありません。

判定の基準は「生成した画像を商用利用できること」です。

---

## Tier A — 商用利用可（ライセンス文面が明確）

こちらだけを使えば、ライセンス面での事故はまず起きません。

### Checkpoint

| モデル | 配布元 | ライセンス | 用途 |
|---|---|---|---|
| **FLUX.1 [schnell]** | `black-forest-labs/FLUX.1-schnell` | **Apache-2.0** | 最推奨。**画像内の文字を正しく描ける**唯一のTier A。4〜8ステップで生成が速い |
| **Stable Diffusion XL Base 1.0** | `stabilityai/stable-diffusion-xl-base-1.0` | CreativeML Open RAIL++-M | 汎用。LoRA/ControlNetの資産が最も豊富 |
| **SDXL Refiner 1.0** | `stabilityai/stable-diffusion-xl-refiner-1.0` | CreativeML Open RAIL++-M | SDXLの仕上げ用（任意） |
| **Stable Diffusion 2.1** | `stabilityai/stable-diffusion-2-1` | CreativeML Open RAIL++-M | 軽量。768px |
| **Stable Diffusion 1.5** | `stable-diffusion-v1-5/stable-diffusion-v1-5` | CreativeML OpenRAIL-M | 軽量・低VRAM向け。派生モデルが膨大 |

> OpenRAIL 系は商用利用を許可していますが、**使用用途の制限条項**（違法行為・差別・
> 虚偽情報の生成などの禁止）があります。この制限は再配布時にも引き継ぐ必要があります。

### VAE（ノイズ・色崩れ対策に必須）

| モデル | 配布元 | ライセンス | 用途 |
|---|---|---|---|
| **sdxl-vae-fp16-fix** | `madebyollin/sdxl-vae-fp16-fix` | MIT | SDXL用。**fp16でのNaN（真っ黒画像）を根本的に防ぐ** |
| **vae-ft-mse-840000** | `stabilityai/sd-vae-ft-mse` | MIT | SD1.5用。紫の斑点・色あせを防ぐ |

### アップスケーラ

| モデル | ライセンス | 備考 |
|---|---|---|
| **R-ESRGAN 4x+** | BSD-3-Clause | WebUIに同梱。追加DL不要 |
| **Real-ESRGAN / anime6B** | BSD-3-Clause | 同上 |

> 定番の `4x-UltraSharp` はライセンス表記が明確でないため、この許可リストには**含めません**。

---

## Tier B — 条件付き商用可（条件を読んでから使う）

| モデル | ライセンス | 条件 |
|---|---|---|
| Stable Diffusion 3.5 Large / Medium | Stability AI Community License | 年間売上 **100万USD未満**の個人・法人は商用無償。超える場合は Enterprise 契約が必要 |
| Playground v2.5 | Playground v2.5 Community License | 商用可だが月間アクティブユーザ数の上限あり |
| Civitai系（Pony, Animagine 等） | Fair AI Public License 1.0-SD ほか | 商用可のものが多いが、**派生物の公開義務**が付くことがある。必ず個別に監査 |

Tier B を使う場合は、自分の事業規模が条件内に収まっているかを先に確認してください。

---

## Tier C — 商用利用不可（絶対に models フォルダに入れない）

間違えやすいものを明示しておきます。**名前が似ているだけで条件が正反対**です。

| モデル | 理由 |
|---|---|
| **FLUX.1 [dev]** | 非商用ライセンス。`[schnell]`（Apache-2.0）と混同しやすい最大の罠 |
| **FLUX.1 [pro]** | API専用・非商用配布 |
| **SDXL Turbo / SD Turbo** | Stability AI Non-Commercial Research License |
| **Stable Video Diffusion** | 非商用研究ライセンス |
| Civitai で商用欄が赤バツのモデル | `allowCommercialUse: None` |

---

## 導入手順

1. Tier A のモデルだけをダウンロードする
2. 配置する
   ```
   webui/models/Stable-diffusion/   ← Checkpoint
   webui/models/VAE/                ← VAE
   webui/models/Lora/               ← LoRA
   ```
3. **配置後に必ず監査する**
   ```bash
   python tools/license_audit.py scan "webui/models"
   ```
4. `× 商用不可` が出たら削除、`△ 要確認` は配布元のライセンス条文を自分で確認

LoRA は個別に名前を挙げていません。Civitai の LoRA はバージョンごとに許諾が違い、
作者があとから変更することも多いためです。**必ず監査ツールで判定してください** ——
それがこのキットで LoRA を安全に扱う唯一の方法です。
