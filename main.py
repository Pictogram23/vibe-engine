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
st.set_page_config(page_title="Vibe Engine Debugger", layout="wide")

# --- 2. APIの初期化と生存確認 ---
if not API_KEY:
    st.error(
        "🔑 APIキーが見つかりません。環境変数 `GEMINI_API_KEY` を設定してください。"
    )
    st.stop()

client = genai.Client(api_key=API_KEY)
MODEL_ID = "gemini-1.5-flash"  # 安定性のために一旦1.5固定


# --- 3. ユーティリティ関数 ---
def run_command(command: list):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
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


# --- 4. Streamlit UI ---
st.title("🚀 Vibe Coding Engine Manager")

# サイドバー
with st.sidebar:
    st.header("⚙️ システム状態")

    # 【追加】疎通テストボタン
    if st.button("📡 Gemini疎通テスト実行"):
        with st.spinner("通信中..."):
            try:
                test_res = client.models.generate_content(
                    model=MODEL_ID, contents="Hello! Respond with 'Ready to Vibe!'"
                )
                if test_res and test_res.text:
                    st.success(f"通信成功: {test_res.text}")
                else:
                    st.warning("通信はしましたが、返答が空でした。")
            except Exception as e:
                st.error(f"通信エラー: {e}")

    st.divider()
    st.header("Project Setup")
    with st.form("init_project"):
        proj_name = st.text_input("Project Name", "vibe_game")
        genre = st.selectbox("Genre", ["2D Action", "RPG", "Bullet Hell", "Adventure"])
        desc = st.text_area("Description", "A simple game.")
        init_btn = st.form_submit_button("Initialize Project")

    if init_btn:
        if not Path(RUST_CARGO).exists():
            run_command(["cargo", "init"])
        blueprint_content = f"# Project: {proj_name}\n## 1. Vision\n- Genre: {genre}\n- Description: {desc}\n\n## 2. Implementation Log\n- [x] Initial Setup\n- [ ] Step 1: Window"
        Path(BLUEPRINT_FILE).write_text(blueprint_content, encoding="utf-8")
        st.success("初期化完了！")
        st.rerun()

# メイン表示
col_doc, col_chat = st.columns([1, 1])

with col_doc:
    st.subheader("📄 Blueprint")
    if Path(BLUEPRINT_FILE).exists():
        st.markdown(Path(BLUEPRINT_FILE).read_text(encoding="utf-8"))

with col_chat:
    st.subheader("💬 Vibe Chat")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("次は何を実装する？"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            status_box = st.empty()
            status_box.info("🧠 Geminiが考え中です...")

            try:
                # APIリクエスト
                response = client.models.generate_content(
                    model=MODEL_ID,
                    contents=f"{get_current_context()}\n\n指示: {prompt}\n\n必ず ---CODE_START---, ---CODE_SPLIT---, ---DOC_START--- の形式で出力してください。",
                )

                res_text = response.text if response and response.text else ""

                # 【重要】AIの回答をそのまま表示（パース失敗しても見えるように）
                st.markdown("### AIの生回答:")
                st.code(res_text)

                if "---CODE_START---" in res_text:
                    status_box.info("💾 ファイル書き込み中...")
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

                    st.success("✅ ファイル更新成功！")

                    status_box.info("🛠️ Rustビルドチェック中...")
                    code, out, err = run_command(["cargo", "check"])
                    if code == 0:
                        st.success("🚀 ビルド成功！")
                    else:
                        st.error("⚠️ ビルドエラー")
                        st.code(err)
                else:
                    st.warning("⚠️ 指定フォーマットが見つかりませんでした。")

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": "回答終了。内容を確認してください。",
                    }
                )

            except Exception as e:
                st.error(f"❌ 実行エラー: {e}")
