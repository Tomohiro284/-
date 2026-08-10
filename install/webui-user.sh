#!/usr/bin/env bash
# ============================================================
#  Stable Diffusion WebUI (AUTOMATIC1111 / Forge) 起動設定
#  Linux / macOS 用。webui ディレクトリ直下の webui-user.sh を置き換える。
# ============================================================

# --- 文字化け対策 ---------------------------------------------
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
export LANG="${LANG:-C.UTF-8}"
export LC_ALL="${LC_ALL:-C.UTF-8}"

# --- Python 3.10.x を明示 --------------------------------------
# 3.11 / 3.12 では依存解決が壊れる。
python_cmd="python3.10"
venv_dir="venv"

# --- 起動オプション（1つだけ有効にする）------------------------

# [A] NVIDIA RTX 20/30/40/50 シリーズ（推奨・既定）
export COMMANDLINE_ARGS="--no-half-vae --opt-sdp-no-mem-attention --upcast-sampling --api"

# [B] NVIDIA GTX 16xx（fp16が壊れる個体）
# export COMMANDLINE_ARGS="--precision full --no-half --no-half-vae --opt-sdp-no-mem-attention --api"

# [C] VRAM 6GB 以下
# export COMMANDLINE_ARGS="--medvram --no-half-vae --opt-sdp-no-mem-attention --api"

# [D] VRAM 4GB 以下
# export COMMANDLINE_ARGS="--lowvram --no-half-vae --opt-sdp-no-mem-attention --api"

# [E] AMD ROCm
# export COMMANDLINE_ARGS="--no-half-vae --opt-sdp-no-mem-attention --api"
# export HSA_OVERRIDE_GFX_VERSION=10.3.0

# [F] Apple Silicon (MPS)
# export COMMANDLINE_ARGS="--skip-torch-cuda-test --upcast-sampling --no-half-vae --use-cpu interrogate"
# export PYTORCH_ENABLE_MPS_FALLBACK=1

# [G] CPU のみ
# export COMMANDLINE_ARGS="--skip-torch-cuda-test --use-cpu all --precision full --no-half --no-half-vae"

# --- 再現性の固定 ---------------------------------------------
export CUBLAS_WORKSPACE_CONFIG=":4096:8"

# --- 起動前セルフチェック ---------------------------------------
_kit_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "$_kit_root/tools/doctor.py" ]; then
  if ! "$python_cmd" "$_kit_root/tools/doctor.py" --webui-dir "$PWD"; then
    rc=$?
    if [ "$rc" -ge 2 ]; then
      echo ""
      echo "[中止] 致命的な問題が見つかりました。上のログを確認してください。"
      exit 1
    fi
  fi
fi
