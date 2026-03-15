# Vibe Engine

## Prerequisites (Linux / Ubuntu)
ビルドには以下のシステムライブラリが必要です。

```bash
sudo apt update
sudo apt install -y cmake clang libclang-dev build-essential \
    libasound2-dev libx11-dev libxrandr-dev libxi-dev \
    libgl1-mesa-dev libglu1-mesa-dev libxcursor-dev libxinerama-dev
```

## How to Run
1. APIキーの設定: `export GEMINI_API_KEY='your_key_here'` or `.env`に記載
2. 管理画面の起動: `uv run streamlit run main.py`
3. ゲームの実行: `cargo run`