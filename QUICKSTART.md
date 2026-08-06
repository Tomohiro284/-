# 最速で動かす

「今すぐ画像を作りたい」向け。上から順に速い。**A なら0分**で使えます。

前提として、ローカル実行には **NVIDIA GPU（VRAM 6GB以上）が実質必須**です。
GPUが無い／わからない場合は A を選んでください。

---

## A. ブラウザだけ（0分・インストール不要）

**Hugging Face Spaces** で公開デモを使います。アカウント登録も不要です。

| 用途 | URL |
|---|---|
| 文字が描ける・速い | https://huggingface.co/spaces/black-forest-labs/FLUX.1-schnell |
| SDXL標準 | https://huggingface.co/spaces/hysts/SD-XL |

- モデルは **FLUX.1 [schnell] = Apache-2.0**、**SDXL Base = OpenRAIL++-M**。どちらも**商用利用可**です
- 環境構築が無いので、**ノイズ・文字化け・バグの発生要因がそもそも存在しません**
- 制約: 混雑時は待ち時間あり。LoRA は使えません。生成枚数の制限あり

**まずこれで目的が足りるか確かめてください。** 足りるなら以下は不要です。

---

## B. アプリを入れる（15分・設定項目がほぼ無い）

**Fooocus** — 設定をユーザーに触らせない設計なので、**設定ミス由来の不具合が起きません**。
サンプラー・CFG・VAE は内部で最適値に固定済みです。

1. https://github.com/lllyasviel/Fooocus のリリースから Windows 版をダウンロード
2. **半角英数のみのパス**に解凍する（例 `C:\fooocus`）。日本語パスは必ず壊れます
3. `run.bat` を実行（初回はモデルを自動ダウンロードするため時間がかかります）
4. ブラウザが自動で開いたら、プロンプトを入れて Generate

**商用利用する場合は起動後にモデルを差し替えてください。** 既定モデルはライセンス条件が
版によって変わるため、`models/allowlist.md` の Tier A（SDXL Base 1.0 など）を
`Fooocus\models\checkpoints\` に置き、画面上部の Model で選び直します。

Mac の場合は **Draw Things**（App Store・無料）が同等に簡単です。

---

## C. WebUI版（AUTOMATIC1111 / Forge）

LoRA・ControlNet・シード固定など、全部を自分で制御したい場合。

### 自動セットアップ（推奨）

インストール先の検査・取得・起動スクリプト配置・推奨設定の適用・セルフチェックを
まとめて実行します。

```bash
git clone https://github.com/Tomohiro284/-.git sd-kit
cd sd-kit
python install/setup.py --dir C:\sd\webui
```

| オプション | 意味 |
|---|---|
| `--variant forge` | 本家ではなく Forge（高速版）を入れる |
| `--preset sd15` | SD1.5 向けのサンプラー設定にする（既定は `sdxl`） |
| `--python <path>` | Python 3.10 の場所を明示する |
| `--dry-run` | 何も書き込まずに手順だけ確認する |

**非ASCIIパス・容量不足・git未導入は、何かを書き込む前に検出して中止します。**
壊れた状態が作られることはありません。

続けてモデルを取得します（Tier A のみ・レジューム対応）。

```bash
python tools/fetch_models.py --webui-dir C:\sd\webui --set sdxl   # 約7.2GB
python tools/license_audit.py scan "C:\sd\webui\models"           # ライセンス監査
```

あとはGPU別オプションの選択だけです。画面の案内に従ってください。

### 手動でやる場合

→ **[docs/01-setup.md](docs/01-setup.md)** を手順1から

A・B と違い、LoRA・ControlNet・Hires.fix・シード固定などを自分で制御できます。
その代わり環境構築の手間と不具合のリスクを引き受けることになります。

---

## どれを選ぶか

| 状況 | 選ぶもの |
|---|---|
| とにかく今すぐ画像が欲しい | **A** |
| GPUが無い / 持っているか不明 | **A** |
| 自分のPCで何枚でも作りたい、設定はしたくない | **B** |
| LoRAを使いたい / シードを厳密に管理したい | **C** |

**迷ったら A → 物足りなければ B → さらに必要なら C** の順で移ってください。
いきなり C から始めると、環境構築で詰まって画像を1枚も作れないまま終わりがちです。
