import streamlit as st
import google.generativeai as genai
from PIL import Image
import uuid # 新增：用來產生每筆紀錄的專屬 ID

# ==========================================
# 1. 網頁基本設定
# ==========================================
st.set_page_config(page_title="FB 直播留言自動生成器", page_icon="🔥", layout="wide")
st.title("🔥 FB 直播留言自動生成器 (極速進階版)")

# ==========================================
# 2. 設定 Google Gemini API
# ==========================================
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
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

# 單筆刪除的處理函式
def delete_record(record_id):
    st.session_state.history = [r for r in st.session_state.history if r["id"] != record_id]

# ==========================================
# 4. 主要版面設定區 (UI 介面)
# ==========================================
col_left, col_right = st.columns([1.2, 1])

with col_left:
    st.markdown("### 📦 步驟一：商品資訊")
    host_name = st.text_input("直播主稱呼/綽號 (可選填，多個可用逗號分隔，例如：明哥、闆娘)")
    product_name = st.text_input("商品名稱 (例如：大黑天唐卡、冰絲寬褲、魚油)")
    product_desc = st.text_area("產品特色/補充說明 (可選填，直接貼上廠商文案)", height=100)
    
    is_repurchase = st.radio(
        "這款商品以前有賣過嗎？",
        ["🆕 初次上架 (留言強調：期待、嘗鮮、想看介紹)", "🔥 曾經熱賣 (留言強調：回購、好用囤貨、終於又開賣了)"]
    )
    uploaded_file = st.file_uploader("📸 貼上截圖或上傳商品照 (不知道名稱直接傳圖，AI 會自己看！)", type=['png', 'jpg', 'jpeg'])
    
with col_right:
    st.markdown("### ⚙️ 步驟二：留言參數與人設")
    buyer_personas = st.multiselect(
        "👥 留言者人設/輪廓 (可複選，AI 會自動混搭語氣)",
        ["一般大眾 (預設)", "年輕女性/女大生", "貴婦/財富自由的女生", "精打細算的媽媽", "年輕男性/男大生", "中年大叔/爸爸", "長輩/銀髮族"],
        default=["一般大眾 (預設)"]
    )
    
    num_comments = st.slider("要生成幾則留言？", min_value=5, max_value=300, value=20)
    emoji_freq = st.slider("表情符號頻率 (0 代表不要，數值越大代表越多)", 0, 5, 2)
    length_req = st.selectbox("字數長度要求", ["長短隨機交錯 (5-50字，最自然)", "極短 (5-15字)", "一般長度 (15-30字)"])

    st.markdown("### 🎨 步驟三：留言風格比例設定")
    st.caption("系統會自動依比例分配，不需剛好湊滿 100")
    style_desire = st.number_input("渴望型比例 (求關注/想買)", min_value=0, value=20, step=10)
    style_value = st.number_input("划算型比例 (稱讚CP值高/直接下單)", min_value=0, value=20, step=10)
    style_effect = st.number_input("功效/體驗型比例 (好用/有感)", min_value=0, value=60, step=10)

st.markdown("---")

# ==========================================
# 5. 生成按鈕與 AI 處理邏輯
# ==========================================
generate_clicked = st.button("🚀 一鍵生成留言", use_container_width=True, type="primary")

if generate_clicked:
    if not product_name and uploaded_file is None:
        st.warning("請至少輸入「商品名稱」或「上傳商品圖片」，AI 才知道要寫什麼喔！")
    else:
        with st.spinner("AI 靈感湧現中，請稍候... (若數量較多請耐心等待)"):
            try:
                host_instruction = host_name if host_name else "主播、老闆、闆娘"
                persona_instruction = "、".join(buyer_personas)

                prompt = f"""
                你現在是一位專業的 FB 直播互動觀眾。請幫我生成 {num_comments} 則看直播時會留的留言。
                
                【商品資訊】
                商品名稱：{product_name if product_name else '請參考圖片推測商品'}
                商品特色：{product_desc if product_desc else '無'}
                
                【嚴格留言要求】
                1. 總數：必須產生 {num_comments} 則留言，請用條列式輸出。
                2. 字數長度：{length_req}。
                3. 語氣限制 (極重要)：貼近台灣 FB 直播買家習慣。**絕對禁止出現任何質疑、懷疑或比價的負面語氣**。所有留言都必須是正向支持、稱讚划算、期待或決定下單。
                4. 禁忌命令：絕對禁止生成只有「+1」、「+2」或單純「商品名+1」的無意義留言！每一則都必須是完整的對話。
                5. 稱呼限制 (極重要)：**絕對禁止在留言中使用「小編」這個詞**！如果有需要稱呼對方，請隨機使用以下稱呼：【{host_instruction}】。大約每 10 則留言出現 1 次稱呼即可 (約10%機率)，其餘 90% 留言請直接講重點，不要加任何稱呼。
                6. 留言者人設 (極重要)：請將這 {num_comments} 則留言，分配給以下這些不同身分的買家來發言：【{persona_instruction}】。請生動地模仿這些族群各自的口吻與關注點，讓留言區看起來是形形色色的人在互動。
                7. 表情符號：{'絕對不要使用表情符號' if emoji_freq == 0 else f'適度使用表情符號 (活躍度 {emoji_freq}/5)'}。
                8. 風格分配：請大約依照以下比例混搭撰寫：
                   - 渴望型(求關注/想買/正向驚呼)：{style_desire}份
                   - 划算型(覺得超值/直接下單/詢問組合優惠)：{style_value}份
                   - 功效/體驗型(好用/有感)：{style_effect}份
                """
                
                if "曾經熱賣" in is_repurchase:
                    prompt += "\n9. 【特別要求：老客回購】：這款商品曾大熱賣，請在部分留言大量加入「之前買過超好用」、「這次要多囤幾組」、「終於等到了」、「上次沒搶到這次一定要買」等熱情回購語氣。"
                else:
                    prompt += "\n9. 【特別要求：初次上架】：這是新品，請在部分留言加入「想試試看」、「感覺很厲害」、「坐等介紹」、「這什麼好特別喔」等期待嘗鮮語氣。"
                
                inputs = [prompt]
                if uploaded_file is not None:
                    image_data = Image.open(uploaded_file)
                    inputs.append(image_data)
                    prompt += "\n10. 【圖片輔助】：我有附上商品圖片，請觀察圖片中的特徵、顏色、包裝或文字，把這些細節融入留言中，讓留言更真實。"

                response = model.generate_content(inputs)
                
                # 寫入歷史紀錄，並給予專屬 ID 以利單筆刪除
                st.session_state.history.insert(0, {
                    "id": str(uuid.uuid4()),
                    "product": product_name if product_name else "📸 圖片商品",
                    "content": response.text
                })
                
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "quota" in error_msg.lower():
                    st.error("⚠️ 觸發流量限制：點擊太快或生成字數過多。請暫停動作等待 1 分鐘後再試。")
                else:
                    st.error(f"❌ 發生錯誤，請截圖給工程師：\n{error_msg}")

# ==========================================
# 6. 直接在主畫面下方顯示「最新一筆」結果
# ==========================================
if st.session_state.history:
    st.markdown("### ✨ 最新生成結果")
    latest_record = st.session_state.history[0]
    st.info(f"當前商品：{latest_record['product']}")
    # 直接在主畫面印出最新留言，方便立刻複製
    st.write(latest_record['content'])

# ==========================================
# 7. 側邊欄：顯示歷史紀錄與單筆刪除
# ==========================================
st.sidebar.markdown("### 📝 歷史生成紀錄")

if st.sidebar.button("🗑️ 清空所有紀錄", use_container_width=True):
    st.session_state.history = []
    st.rerun()

st.sidebar.markdown("---")

if not st.session_state.history:
    st.sidebar.info("目前無歷史紀錄。")
else:
    for record in st.session_state.history:
        with st.sidebar.expander(f"📂 {record['product']}"):
            # 單筆刪除按鈕
            st.button("❌ 刪除此筆", key=f"del_{record['id']}", on_click=delete_record, args=(record['id'],))
            st.write(record['content'])
