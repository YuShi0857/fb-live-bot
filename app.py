import streamlit as st
import google.generativeai as genai
from PIL import Image

# ==========================================
# 1. 網頁基本設定
# ==========================================
st.set_page_config(page_title="FB 直播留言自動生成器", page_icon="🔥", layout="wide")
st.title("🔥 FB 直播留言自動生成器 (極速進階版)")

# ==========================================
# 2. 設定 Google Gemini API
# ==========================================
# 讀取 Streamlit Secrets 中的 API Key
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# 模型設定 (依照 Google 系統要求使用 3.6-flash，享有高額度與視覺辨識能力)
generation_config = {
  "temperature": 0.9,
  "top_p": 0.95,
}
model = genai.GenerativeModel('gemini-3.6-flash', generation_config=generation_config)

# ==========================================
# 3. 初始化歷史紀錄暫存 (Session State)
# ==========================================
if "history" not in st.session_state:
    st.session_state.history = []

# ==========================================
# 4. 側邊欄或主要版面設定區 (UI 介面)
# ==========================================
col_left, col_right = st.columns([1.2, 1])

with col_left:
    st.markdown("### 📦 步驟一：商品資訊")
    product_name = st.text_input("商品名稱 (例如：大黑天唐卡、冰絲寬褲、魚油)")
    product_desc = st.text_area("產品特色/補充說明 (可選填，直接貼上廠商文案)", height=100)
    
    # 回購語氣與圖片上傳
    is_repurchase = st.radio(
        "這款商品以前有賣過嗎？",
        ["🆕 初次上架 (留言強調：期待、嘗鮮、想看介紹)", "🔥 曾經熱賣 (留言強調：回購、好用囤貨、終於又開賣了)"]
    )
    uploaded_file = st.file_uploader("📸 貼上截圖或上傳商品照 (不知道名稱直接傳圖，AI 會自己看！)", type=['png', 'jpg', 'jpeg'])
    
    st.markdown("### ⚙️ 步驟二：留言參數設定")
    # 擴充至 300 則
    num_comments = st.slider("要生成幾則留言？", min_value=5, max_value=300, value=20)
    emoji_freq = st.slider("表情符號頻率 (0 代表不要，數值越大代表越多)", 0, 5, 2)
    length_req = st.selectbox("字數長度要求", ["長短隨機交錯 (5-50字，最自然)", "極短 (5-15字)", "一般長度 (15-30字)"])

with col_right:
    st.markdown("### 🎨 步驟三：留言風格比例設定")
    st.caption("系統會自動依比例分配，不需剛好湊滿 100")
    style_desire = st.number_input("渴望型比例 (求關注/想買)", min_value=0, value=20, step=10)
    style_value = st.number_input("划算型比例 (CP值/問價格)", min_value=0, value=20, step=10)
    style_effect = st.number_input("功效/體驗型比例 (好用/有感)", min_value=0, value=60, step=10)

st.markdown("---")

# ==========================================
# 5. 生成按鈕與 AI 處理邏輯
# ==========================================
col_btn1, col_btn2 = st.columns([1, 5])
with col_btn1:
    generate_clicked = st.button("🚀 一鍵生成留言", use_container_width=True)
with col_btn2:
    if st.button("🗑️ 清空所有紀錄"):
        st.session_state.history = []
        st.rerun()

if generate_clicked:
    if not product_name and uploaded_file is None:
        st.warning("請至少輸入「商品名稱」或「上傳商品圖片」，AI 才知道要寫什麼喔！")
    else:
        with st.spinner("AI 靈感湧現中，請稍候... (若數量較多請耐心等待)"):
            try:
                # 建立 AI 指令 (Prompt) - 加入了嚴格的禁忌命令
                prompt = f"""
                你現在是一位專業的 FB 直播互動小編。請幫我生成 {num_comments} 則觀眾在看直播時會留的留言。
                
                【商品資訊】
                商品名稱：{product_name if product_name else '請參考圖片推測商品'}
                商品特色：{product_desc if product_desc else '無'}
                
                【留言要求】
                1. 總數：必須產生 {num_comments} 則留言，請用條列式輸出。
                2. 字數長度：{length_req}。
                3. 語氣：貼近台灣 FB 直播買家習慣（接地氣、口語化、不要太像機器人）。
                4. 禁忌命令：絕對禁止生成只有「+1」、「+2」或單純「商品名+1」的留言！每一則都必須是完整的對話，要有具體的問題、稱讚、期待或互動心得。
                5. 表情符號：{'絕對不要使用表情符號' if emoji_freq == 0 else f'適度使用表情符號 (活躍度 {emoji_freq}/5)'}。
                6. 風格分配：請大約依照以下比例混搭撰寫：
                   - 渴望型(求關注/想買)：{style_desire}份
                   - 划算型(CP值/問價格)：{style_value}份
                   - 功效/體驗型(好用/有感)：{style_effect}份
                """
                
                # 附加回購語氣
                if "曾經熱賣" in is_repurchase:
                    prompt += "\n7. 【特別要求：老客回購】：這款商品曾大熱賣，請在部分留言大量加入「之前買過超好用」、「這次要多囤幾組」、「終於等到了」、「上次沒搶到這次一定要買」等熱情回購語氣。"
                else:
                    prompt += "\n7. 【特別要求：初次上架】：這是新品，請在部分留言加入「想試試看」、「感覺很厲害」、「坐等介紹」、「這什麼好特別喔」等期待嘗鮮語氣。"
                
                # 準備輸入資料 (文字 + 圖片)
                inputs = [prompt]
                if uploaded_file is not None:
                    # 如果有上傳圖片，把圖片轉換給 Gemini
                    image_data = Image.open(uploaded_file)
                    inputs.append(image_data)
                    prompt += "\n8. 【圖片輔助】：我有附上商品圖片，請觀察圖片中的特徵、顏色、包裝或文字，把這些細節融入留言中，讓留言更真實。"

                # 呼叫 Gemini API
                response = model.generate_content(inputs)
                
                # 將最新結果存入歷史紀錄的最前面
                st.session_state.history.insert(0, {
                    "product": product_name if product_name else "📸 圖片商品",
                    "content": response.text
                })
                st.success("🎉 生成成功！")
                
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "quota" in error_msg.lower():
                    st.error("⚠️ 觸發流量限制：點擊太快或生成字數過多。請暫停動作等待 1 分鐘後再試。")
                else:
                    st.error(f"❌ 發生錯誤，請截圖給工程師：\n{error_msg}")

# ==========================================
# 6. 顯示歷史紀錄
# ==========================================
st.markdown("### 📝 生成紀錄區")
if not st.session_state.history:
    st.info("目前還沒有紀錄，設定好參數後點擊「一鍵生成留言」吧！")
else:
    for i, record in enumerate(st.session_state.history):
        with st.expander(f"📌 {record['product']} (最新)" if i == 0 else f"📂 {record['product']}", expanded=(i == 0)):
            st.write(record['content'])
