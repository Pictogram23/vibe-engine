import streamlit as st
import subprocess
import os
from pathlib import Path
from google import genai

# --- 1. 定数・設定 ---
BLUEPRINT_FILE = "blueprint.md"
RUST_MAIN = "src/main.rs"
RUST_CARGO = "Cargo.toml"
API_KEY = os.getenv("GEMINI_API_KEY")

# テンプレート化されたシステム指示（AIの役割と合言葉を固定）
SYSTEM_INSTRUCTION = """
あなたはRustゲーム開発のスペシャリストです。
ユーザーの指示に基づき、Cargo.toml、src/main.rs、blueprint.md を更新してください。

【厳守ルール】
1. 出力は必ず以下のセパレーターで区切ること。これら以外の挨拶や解説は一切不要です。
---CODE_START---
(Cargo.tomlの内容)
---CODE_SPLIT---
(src/main.rsの内容)
---DOC_START---
(blueprint.mdの内容)

2. Rustの所有権、型システム、最新のAPI仕様（raylib-rs v5.5等）を正しく扱ってください。
3. エラー修正の依頼があった場合は、提供されたエラーログを解析し、根本原因を解決してください。
"""

st.set_page_config(page_title="Vibe Engine v3.0", layout="wide")

if not API_KEY:
    st.error(
        "🔑 APIキーが見つかりません。環境変数 `GEMINI_API_KEY` を設定してください。"
    )
    st.stop()

client = genai.Client(api_key=API_KEY)
MODEL_ID = "gemini-2.5-flash"

# --- 2. ユーティリティ関数 ---


def run_command(command: list):
    """コマンド実行と結果取得"""
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def get_current_context():
    """設計図とコードの現状を取得"""
    context = "### Current Blueprint ###\n"
    if Path(BLUEPRINT_FILE).exists():
        context += Path(BLUEPRINT_FILE).read_text(encoding="utf-8")
    if Path(RUST_MAIN).exists():
        context += "\n\n### Current Main.rs ###\n"
        context += Path(RUST_MAIN).read_text(encoding="utf-8")
    return context


def process_vibe(instruction_text):
    """AIへのリクエスト、ファイル更新、ビルドチェックを一括で行う"""
    status = st.empty()
    status.info("🧠 Geminiが思考中...")

    try:
        # プロンプトの組み立て（システム指示 + コンテキスト + 個別指示）
        full_req = f"{SYSTEM_INSTRUCTION}\n\n{get_current_context()}\n\n【指示】\n{instruction_text}"

        response = client.models.generate_content(model=MODEL_ID, contents=full_req)
        res_text = response.text if response and response.text else ""

        with st.expander("AI Raw Output", expanded=False):
            st.code(res_text)

        if "---CODE_START---" in res_text:
            status.info("💾 ファイルを同期中...")
            parts = res_text.split("---CODE_START---")[1]
            cargo_content = parts.split("---CODE_SPLIT---")[0].strip()
            main_content = (
                parts.split("---CODE_SPLIT---")[1].split("---DOC_START---")[0].strip()
            )
            doc_content = res_text.split("---DOC_START---")[1].strip()

            Path(RUST_CARGO).write_text(cargo_content, encoding="utf-8")
            Path(RUST_MAIN).write_text(main_content, encoding="utf-8")
            Path(BLUEPRINT_FILE).write_text(doc_content, encoding="utf-8")

            st.success("✅ ファイルを更新しました！")

            status.info("🛠️ ビルドチェック中...")
            code, out, err = run_command(["cargo", "check"])

            if code == 0:
                st.success("🚀 ビルド成功！")
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": "実装が完了しました。`cargo run` で確認してください！",
                    }
                )
            else:
                st.error("⚠️ ビルドエラーが発生しました。")
                st.code(err)
                # エラー内容を保持して自動修正ボタンを有効化
                st.session_state.last_error = err
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": "ビルドエラーを検知しました。下の「自動修正」ボタンで直せます。",
                    }
                )
        else:
            st.warning("⚠️ フォーマットエラー。生回答を確認してください。")

    except Exception as e:
        st.error(f"❌ エラー: {e}")

    status.empty()


# --- 3. Streamlit UI ---

with st.sidebar:
    st.header("⚙️ System")
    if st.button("📡 Gemini疎通テスト"):
        res = client.models.generate_content(model=MODEL_ID, contents="Hello!")
        st.success("OK")

    st.divider()
    st.header("📂 Project Setup")
    with st.form("init_project"):
        proj_name = st.text_input("Project Name", "vibe_game")
        genre = st.selectbox("Genre", ["2D Action", "RPG", "Bullet Hell", "Adventure"])
        desc = st.text_area("Description", "A simple game.")
        col_w, col_h = st.columns(2)
        w_size = col_w.number_input("Width", 1280)
        h_size = col_h.number_input("Height", 720)
        fps = st.slider("Target FPS", 30, 144, 60)
        if st.form_submit_button("Initialize Project"):
            if not Path(RUST_CARGO).exists():
                run_command(["cargo", "init"])
            blueprint = f"# Project: {proj_name}\n## Vision\n- Genre: {genre}\n- Desc: {desc}\n\n## Specs\n- Window: {w_size}x{h_size}\n- FPS: {fps}\n\n## Log\n- [x] Init"
            Path(BLUEPRINT_FILE).write_text(blueprint, encoding="utf-8")
            st.rerun()

col_doc, col_chat = st.columns([1, 1])

with col_doc:
    st.subheader("📄 Blueprint")
    if Path(BLUEPRINT_FILE).exists():
        st.markdown(Path(BLUEPRINT_FILE).read_text(encoding="utf-8"))

with col_chat:
    st.subheader("💬 Vibe Chat")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_error" not in st.session_state:
        st.session_state.last_error = None

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ユーザー入力
    if prompt := st.chat_input("例：画面を青色にして"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

    # 指示の実行（リラン後に処理）
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.chat_message("assistant"):
            process_vibe(st.session_state.messages[-1]["content"])

    # 自動修正ボタン（エラーがある場合のみ表示）
    if st.session_state.last_error:
        if st.button("🛠️ AIでこのエラーを自動修正する"):
            fix_msg = f"以下のビルドエラーを修正してください。\n\n【エラーログ】\n{st.session_state.last_error}"
            st.session_state.last_error = None  # 一回使ったらクリア
            with st.chat_message("assistant"):
                process_vibe(fix_msg)
            st.rerun()
