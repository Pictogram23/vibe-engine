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

# ページ設定
st.set_page_config(page_title="Vibe Engine v2.5", layout="wide")

# APIの初期化
if not API_KEY:
    st.error(
        "🔑 APIキーが見つかりません。環境変数 `GEMINI_API_KEY` を設定してください。"
    )
    st.stop()

client = genai.Client(api_key=API_KEY)
MODEL_ID = "gemini-2.5-flash"  # 疎通に成功したバージョンを指定


# --- 2. ユーティリティ関数 ---
def run_command(command: list):
    try:
        # 初回のビルドは時間がかかるため timeout を長めに設定
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def get_current_context():
    context = "### Current Blueprint ###\n"
    if Path(BLUEPRINT_FILE).exists():
        context += Path(BLUEPRINT_FILE).read_text(encoding="utf-8")
    if Path(RUST_MAIN).exists():
        context += "\n\n### Current Main.rs ###\n"
        context += Path(RUST_MAIN).read_text(encoding="utf-8")
    return context


# --- 3. Streamlit UI ---
st.title("🚀 Vibe Coding Engine Manager (v2.5)")

# サイドバー: プロジェクト設定 & ステータス
with st.sidebar:
    st.header("⚙️ システム状態")
    if st.button("📡 Gemini疎通テスト"):
        with st.spinner("通信中..."):
            try:
                res = client.models.generate_content(model=MODEL_ID, contents="Hello!")
                st.success("✅ 通信成功")
            except Exception as e:
                st.error(f"❌ エラー: {e}")

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

        init_btn = st.form_submit_button("Initialize Project")

    if init_btn:
        if not Path(RUST_CARGO).exists():
            run_command(["cargo", "init"])

        blueprint_content = f"""# Project: {proj_name}
## 1. Vision
- **Genre:** {genre}
- **Description:** {desc}

## 2. Technical Specs
- **Window Size:** {w_size}x{h_size}
- **Target FPS:** {fps}
- **Language:** Rust
- **Library:** raylib-rs

## 3. Implementation Log
- [x] Initial Project Setup
- [ ] Step 1: Window Initialization
"""
        Path(BLUEPRINT_FILE).write_text(blueprint_content, encoding="utf-8")
        st.success("プロジェクトを初期化しました！")
        st.rerun()

# メイン表示エリア
col_doc, col_chat = st.columns([1, 1])

with col_doc:
    st.subheader("📄 Current Blueprint")
    if Path(BLUEPRINT_FILE).exists():
        st.markdown(Path(BLUEPRINT_FILE).read_text(encoding="utf-8"))
    else:
        st.info("サイドバーからプロジェクトを初期化してください。")

with col_chat:
    st.subheader("💬 Vibe Chat")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("実装したい機能を伝えてください"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            status = st.empty()
            status.info("🧠 Geminiがコードを生成中...")

            try:
                # APIリクエスト
                full_req = f"""
                あなたはRustゲーム開発者です。以下のドキュメントとコードを更新してください。
                
                {get_current_context()}

                指示: {prompt}

                【出力形式厳守】
                ---CODE_START---
                (Cargo.tomlの内容)
                ---CODE_SPLIT---
                (src/main.rsの内容)
                ---DOC_START---
                (更新されたblueprint.mdの内容)
                """

                response = client.models.generate_content(
                    model=MODEL_ID, contents=full_req
                )
                res_text = response.text if response and response.text else ""

                # AIの回答をデバッグ用に表示
                with st.expander("AI Raw Output", expanded=False):
                    st.code(res_text)

                if "---CODE_START---" in res_text:
                    status.info("💾 ファイルを更新中...")
                    parts = res_text.split("---CODE_START---")[1]
                    cargo_content = parts.split("---CODE_SPLIT---")[0].strip()
                    main_content = (
                        parts.split("---CODE_SPLIT---")[1]
                        .split("---DOC_START---")[0]
                        .strip()
                    )
                    doc_content = res_text.split("---DOC_START---")[1].strip()

                    Path(RUST_CARGO).write_text(cargo_content, encoding="utf-8")
                    Path(RUST_MAIN).write_text(main_content, encoding="utf-8")
                    Path(BLUEPRINT_FILE).write_text(doc_content, encoding="utf-8")

                    st.success("✅ ファイルを更新しました！")

                    # ビルドチェック
                    status.info("🛠️ Rustビルドチェック中 (cargo check)...")
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
                        st.error("⚠️ ビルドエラーが発生しました。修正が必要です。")
                        st.code(err)
                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": "ビルドエラーが発生しました。エラーログを確認してください。",
                            }
                        )
                else:
                    st.warning(
                        "⚠️ フォーマットが正しくありません。生回答を確認してください。"
                    )

            except Exception as e:
                st.error(f"❌ エラー: {e}")

            status.empty()
            st.button("画面を更新")
