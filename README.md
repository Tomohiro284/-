# Stable Diffusion 安定起動キット

ノイズ・文字化け・クラッシュの既知原因を設定で潰し、**商用利用可のモデルだけ**を
使う状態で Stable Diffusion を起動するための設定一式です。

AUTOMATIC1111 WebUI / Forge 用。Windows・Linux・macOS 対応。

---

## クイックスタート

```bash
# 1. 環境を診断する（WebUI導入前でも動きます）
python tools/doctor.py --webui-dir "C:\sd\webui"

# 2. 手持ちのモデルのライセンスを一括監査する
python tools/license_audit.py scan "C:\sd\webui\models"

# 3. 推奨設定を適用する
python tools/apply_config.py --webui-dir "C:\sd\webui"

# 4. 起動スクリプトを配置して起動
copy install\webui-user.bat C:\sd\webui\webui-user.bat
```

初めての場合は **[docs/01-setup.md](docs/01-setup.md) を手順1から**進めてください。

---

## 中身

| パス | 役割 |
|---|---|
| `docs/01-setup.md` | インストールから初回生成までの手順 |
| `docs/02-troubleshooting.md` | 症状別の原因と対処（ノイズ / 文字化け / バグ） |
| `models/allowlist.md` | 商用利用可モデルの許可リストと、除外すべきモデル |
| `install/webui-user.bat` | Windows 起動スクリプト（UTF-8固定・GPU別プリセット） |
| `install/webui-user.sh` | Linux / macOS 起動スクリプト |
| `config/a1111-config.json` | WebUI 設定の推奨値 |
| `config/a1111-ui-config.json` | 生成パラメータの既定値と入力上限 |
| `tools/doctor.py` | 起動前セルフチェック。致命的な問題があれば起動を止める |
| `tools/license_audit.py` | ライセンス監査。ハッシュ照合で既存モデルも判定 |
| `tools/apply_config.py` | 設定を既存環境へ安全にマージ適用 |

---

## この設定が防ぐもの

### ノイズ

| 対策 | 効果 |
|---|---|
| `doctor.py` の fp16 実測チェック | GTX 16xx 系の**真っ黒／全面ノイズ**を起動前に検出 |
| `--no-half-vae` を全プリセットに投入 | VAE の NaN 破綻を防ぐ |
| CFG Scale の入力上限を 9.0 に制限 | 焦げ・極彩色化を入力段階で不可能にする |
| `DPM++ 2M` + Karras + 30ステップ を既定化 | 残留ノイズの出ない組み合わせに固定 |
| Hires denoise 0.4 を既定化 | 高解像度化での構図崩れを防ぐ |
| 出力を PNG 固定 | JPEG圧縮由来のブロックノイズを排除 |

### 文字化け

| 対策 | 効果 |
|---|---|
| `chcp 65001` + `PYTHONUTF8=1` | 日本語Windowsのコンソール／ログ／UIの化けを解消 |
| ファイル名からプロンプトを排除 | 日本語プロンプト由来のファイル名破損・保存失敗を防ぐ |
| `doctor.py` の非ASCIIパス検査 | 日本語ユーザー名による起動失敗を事前に検出 |
| ネガティブプロンプトに文字系を投入 | 画像内のデタラメな文字の出現を抑制 |
| FLUX.1 [schnell] を推奨 | 画像内に**読める英数字**を描ける（Apache-2.0で商用可） |

### バグ

| 対策 | 効果 |
|---|---|
| Python 3.10.x の明示指定 | 依存解決の失敗を防ぐ |
| 拡張機能ゼロで開始 | 起動不能の最頻原因（拡張の依存衝突）を回避 |
| `randn_source: CPU` ほか決定性設定 | 同じシードで**必ず同じ画像**が出る |
| `sd_checkpoint_cache: 0` | モデル切替時のメモリ枯渇による強制終了を防ぐ |
| `.ckpt` 検出時に警告 | pickle 由来の任意コード実行を回避 |
| 起動前 `doctor.py` 自動実行 | 壊れた状態での起動そのものを止める |

---

## ライセンス方針

**判定基準は「生成した画像を商用利用できること」** ＝ Civitai の緑チェック
（API の `allowCommercialUse` に `Image` を含む）です。

目視確認は見落とすので、機械判定します。

```bash
# ダウンロード前に確認
python tools/license_audit.py check https://civitai.com/models/133005

# 手持ちを一括監査（SHA256でCivitaiと照合するので、ファイル名が変わっていても判定可）
python tools/license_audit.py scan "C:\sd\webui\models" --json report.json

# 不合格を自動隔離
python tools/license_audit.py scan "C:\sd\webui\models" --quarantine
```

判定は3種類です。

- `○ 商用可` — そのまま使える
- `× 商用不可` — models フォルダから外す
- `△ 要確認` — Civitai 外（HuggingFace・自作・マージ済み）。配布元の条文を自分で読む

安全側に倒したい場合は `--policy strict` で、画像の商用利用に加えて
サービス提供・再配布まで許可されたモデルだけに絞れます。

具体的なモデル名は **[models/allowlist.md](models/allowlist.md)** を参照してください。
`FLUX.1 [dev]`（非商用）と `FLUX.1 [schnell]`（Apache-2.0）の混同が最大の罠です。

---

## 注意書き

- **「絶対にノイズ・文字化け・バグが起きない」保証はできません。** 上記は既知原因を
  網羅的に潰したもので、実運用でよく起きる不具合はほぼ消えますが、生成AIは確率的に
  動くため、稀に手指の破綻などの品質問題は残ります。ゼロにはなりません。
- **画像内の日本語テキストは、現行のどのモデルでも実用品質になりません。** 文字が
  必要な場合は生成後に画像編集ソフトで載せてください。
- **`models/allowlist.md` は法的助言ではありません。** ライセンスは配布者がいつでも
  変更できます。ダウンロード時点で `license_audit.py` または配布元の LICENSE 本文で
  必ず再確認してください。商用利用の可否について最終的な責任を負うのは利用者です。
- `license_audit.py` は Civitai API v1 の仕様に沿って実装していますが、開発環境から
  civitai.com への通信が遮断されていたため、**実 API に対する疎通確認は未実施**です。
  判定ロジック自体はスタブ応答による単体テストで検証済みです。初回実行時は結果が
  妥当か目視で確認してください。
