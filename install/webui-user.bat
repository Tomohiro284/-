@echo off
rem ============================================================
rem  Stable Diffusion WebUI (AUTOMATIC1111 / Forge) 起動設定
rem  文字化け・ノイズ・クラッシュ対策を全部盛りにしたもの
rem  webui ディレクトリ直下の webui-user.bat を「これで置き換える」
rem ============================================================

rem --- 文字化け対策（ここが最重要）-----------------------------
rem  日本語版 Windows は既定が CP932。UTF-8 に固定しないと
rem  コンソールログ・プロンプト・ファイル名が化ける。
chcp 65001 > nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONLEGACYWINDOWSSTDIO=0

rem --- Python は 3.10.x を明示指定 ------------------------------
rem  3.11 / 3.12 は依存関係が壊れる。3.10.6〜3.10.11 を使う。
rem  下の行を自分の環境のパスに書き換える（半角英数のみのパス）。
set PYTHON="C:\Python310\python.exe"
set GIT=
set VENV_DIR=venv

rem --- 起動オプション -------------------------------------------
rem  お使いのGPUに応じて下の COMMANDLINE_ARGS を1つだけ選び、
rem  他はコメントアウト（行頭に rem）したままにする。

rem [A] NVIDIA RTX 20/30/40/50 シリーズ（推奨・既定）
set COMMANDLINE_ARGS=--no-half-vae --opt-sdp-no-mem-attention --upcast-sampling --api

rem [B] NVIDIA GTX 16xx（1650/1660）: fp16が壊れて真っ黒／ノイズになる個体向け
rem set COMMANDLINE_ARGS=--precision full --no-half --no-half-vae --opt-sdp-no-mem-attention --api

rem [C] VRAM 6GB 以下
rem set COMMANDLINE_ARGS=--medvram --no-half-vae --opt-sdp-no-mem-attention --api

rem [D] VRAM 4GB 以下
rem set COMMANDLINE_ARGS=--lowvram --no-half-vae --opt-sdp-no-mem-attention --api

rem [E] GPUなし（CPUのみ・非常に遅い）
rem set COMMANDLINE_ARGS=--skip-torch-cuda-test --use-cpu all --precision full --no-half --no-half-vae

rem --- 再現性の固定 ---------------------------------------------
set CUBLAS_WORKSPACE_CONFIG=:4096:8

rem --- 起動前セルフチェック --------------------------------------
if exist "%~dp0..\tools\doctor.py" (
  %PYTHON% "%~dp0..\tools\doctor.py" --webui-dir "%CD%"
  if errorlevel 2 (
    echo.
    echo [中止] 致命的な問題が見つかりました。上のログを確認してください。
    pause
    exit /b 1
  )
)

call webui.bat
