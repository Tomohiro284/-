# セットアップ手順

所要時間は回線速度次第で 30分〜1時間程度です。順番どおりに進めてください。
**手順1と2を飛ばすと、後からほぼ確実に不具合が出ます。**

---

## 手順1: インストール先を決める（最重要）

パスに**日本語・空白を含めない**こと。Windows で日本語ユーザー名を使っている場合、
既定の場所にインストールすると確実に壊れます。

```
○ C:\sd\webui
○ D:\ai\webui
× C:\Users\山田太郎\Desktop\Stable Diffusion\
```

Linux / macOS でも同様に、ASCII のみのパスにしてください。

---

## 手順2: Python 3.10.x を入れる

AUTOMATIC1111 は **3.10.x 以外では動きません**。3.11 / 3.12 は依存解決に失敗します。

- Windows: [python.org](https://www.python.org/downloads/release/python-31011/) から
  3.10.11 を入れる。インストール時に **"Add Python to PATH" のチェックは外す**
  （既存のPython環境を壊さないため。パスは起動バッチで直接指定します）
- Linux: `sudo apt install python3.10 python3.10-venv`
- macOS: `brew install python@3.10`

すでに別バージョンが入っていても共存できます。

---

## 手順3: WebUI を入れる

```bash
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git C:/sd/webui
```

Forge（高速版）を使う場合:

```bash
git clone https://github.com/lllyasviel/stable-diffusion-webui-forge.git C:/sd/webui
```

どちらでもこのキットの設定はそのまま使えます。

**この時点では拡張機能を1つも入れないでください。** まず素の状態で動くことを
確認してから、必要なものだけを1つずつ足します（不具合の最頻原因が拡張の衝突です）。

---

## 手順4: モデルを入れる

`models/allowlist.md` の **Tier A** からダウンロードして配置します。

```
C:\sd\webui\models\Stable-diffusion\   ← Checkpoint (.safetensors)
C:\sd\webui\models\VAE\                ← VAE
C:\sd\webui\models\Lora\               ← LoRA
```

最小構成の推奨（これだけで始められます）:

| ファイル | 置き場所 |
|---|---|
| `sd_xl_base_1.0.safetensors` | `models/Stable-diffusion/` |
| `sdxl_vae.safetensors`（fp16-fix版） | `models/VAE/` |

画像内に英数字を描きたい場合は `FLUX.1 [schnell]` も追加してください（Apache-2.0）。

**`.ckpt` ではなく必ず `.safetensors` を選ぶこと。** `.ckpt` は読み込むだけで
任意コードが実行され得ます。

---

## 手順5: ライセンス監査（ここを飛ばさない）

配置したモデルが本当に商用利用可かを、目視ではなく機械的に確認します。

```bash
python tools/license_audit.py scan "C:\sd\webui\models"
```

出力の見方:

```
○ 商用可    ... そのまま使えます
× 商用不可  ... models フォルダから削除してください
△ 要確認    ... Civitai外のモデル。配布元のライセンス条文を自分で読んでください
```

不合格のモデルを自動的に隔離フォルダへ退避することもできます。

```bash
python tools/license_audit.py scan "C:\sd\webui\models" --quarantine
```

より厳しく「モデルの再配布・サービス提供まで許可されたものだけ」に絞る場合:

```bash
python tools/license_audit.py scan "C:\sd\webui\models" --policy strict
```

---

## 手順6: 推奨設定を適用する

```bash
python tools/apply_config.py --webui-dir "C:\sd\webui" --dry-run   # 変更内容を確認
python tools/apply_config.py --webui-dir "C:\sd\webui"             # 適用
```

既存の設定はキー単位でマージされ、モデルパスなどの環境固有設定は保持されます。
適用前に `config.bak-YYYYMMDD-HHMMSS.json` としてバックアップが作られます。

---

## 手順7: 起動スクリプトを置き換える

| OS | コピー元 | コピー先 |
|---|---|---|
| Windows | `install/webui-user.bat` | `C:\sd\webui\webui-user.bat` |
| Linux / macOS | `install/webui-user.sh` | `~/sd/webui/webui-user.sh` |

**中を開いて、環境に合わせて2箇所だけ直します。**

1. `set PYTHON=` を手順2で入れた Python 3.10 の実際のパスに
2. `COMMANDLINE_ARGS` を、お使いのGPUに対応する **[A]〜[G] のうち1つだけ**有効にする
   （他は行頭に `rem` / `#` を付けたまま）

| 環境 | 選ぶもの |
|---|---|
| NVIDIA RTX 20/30/40/50 | **[A]**（既定） |
| NVIDIA GTX 1650 / 1660 | **[B]** — これを選ばないと真っ黒／ノイズ画像になります |
| VRAM 6GB以下 | [C] |
| VRAM 4GB以下 | [D] |
| AMD (ROCm) | [E] |
| Apple Silicon | [F] |
| GPUなし | [G] |

---

## 手順8: 起動する

```bash
# Windows
C:\sd\webui\webui-user.bat

# Linux / macOS
cd ~/sd/webui && ./webui.sh
```

起動スクリプトは WebUI 本体を立ち上げる前に `doctor.py` を自動実行します。

```
[   OK ] Python 3.10.11
[   OK ] 文字コード UTF-8 (stdout=utf-8, fs=utf-8)
[   OK ] パスは安全: C:\sd\webui
[   OK ] GPU: NVIDIA GeForce RTX 4070 (compute 8.9, VRAM 12.0GB)
[   OK ] fp16 演算の健全性チェック 合格（黒画像・全面ノイズのリスクなし）
```

**致命** が出た場合は起動を中止します。表示された対処を行ってから再実行してください。
問題がなければブラウザで `http://127.0.0.1:7860` が開きます。

---

## 手順9: 動作確認

最初の1枚は、必ず既定値のまま生成してください（設定を変えるのは動くと確認した後）。

```
プロンプト        : a photograph of a red apple on a wooden table, natural light
ネガティブ        : （推奨設定で投入済み。そのまま）
Sampling method   : DPM++ 2M
Schedule type     : Karras
Sampling steps    : 30
CFG Scale         : 5.0
Size              : 1024 x 1024
Seed              : 12345
```

- 破綻のないリンゴの写真が出れば成功です
- ノイズ・黒画像が出た場合は `docs/02-troubleshooting.md` の 1-1 / 1-2 へ
- 同じシードで2回生成し、**まったく同じ画像**になることも確認してください
  （ならない場合は 3-3 へ）
