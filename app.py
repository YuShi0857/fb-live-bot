import streamlit as st
import google.generativeai as genai
from PIL import Image
import uuid

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
        ["通用 (不分性別年齡，最百搭)", "年輕女性/女大生", "貴婦/財富自由的女生", "精打細算的媽媽", "年輕男性/男大生", "中年大叔/爸爸", "長輩/銀髮族"],
        default=["通用 (不分性別年齡，最百搭)"]
    )
    
    num_comments = st.slider("要生成幾則留言？", min_value=5, max_value=300, value=20)
    emoji_freq = st.slider("表情符號頻率 (0 代表不要，數值越大代表越多)", 0, 5, 2)
    length_req = st.selectbox("字數長度要求", ["長短隨機交錯 (5-50字，最自然)", "極短 (5-15字)", "一般長度 (15-30字)"])

    st.markdown("### 🎨 步驟三：留言風格比例設定")
    st.caption("系統會自動依比例分配，不需剛好湊滿 100")
    
    col_style1, col_style2 = st.columns(2)
    with col_style1:
        style_desire = st.number_input("渴望型 (求關注/想買)", min_value=0, value=15, step=5)
        style_value = st.number_input("划算型 (稱讚CP值/下單)", min_value=0, value=15, step=5)
        style_effect = st.number_input("功效型 (期待效果)", min_value=0, value=15, step=5)
    with col_style2:
        style_question = st.number_input("提問型 (正向發問細節)", min_value=0, value=15, step=5)
        style_feedback = st.number_input("反饋型 (使用心得/推薦)", min_value=0, value=25, step=5)
        style_interaction = st.number_input("互動型 (跟主播/觀眾互動)", min_value=0, value=15, step=5)

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
                
                # 調整長短交錯邏輯：短句不再追求極致短，而是要求「簡短但完整」
                if length_req == "長短隨機交錯 (5-50字，最自然)":
                    length_prompt = "【極致長短交錯】(極重要！) 嚴禁每則留言長度都差不多！請強制分配：大約 30% 是「簡短但語意完整」的句子 (約 10-15 字，例如「這組看起來很不錯，想買來試試」)，40% 是中等長度 (20-30字)，30% 是豐富的長句心得 (30-50字)。"
                else:
                    length_prompt = f"字數長度：{length_req}。注意：即使要求短字數，也必須是語意完整的通順短句。"

                prompt = f"""
                你現在是一位專業的 FB 直播互動觀眾。請幫我生成 {num_comments} 則看直播時會留的留言。
                
                【商品資訊】
                商品名稱：{product_name if product_name else '請參考圖片推測商品'}
                商品特色：{product_desc if product_desc else '無'}
                
                【嚴格留言要求】
                1. 總數：必須產生 {num_comments} 則留言，請用條列式輸出。
                2. 字數要求：{length_prompt}
                3. 語氣限制 (極重要)：貼近台灣 FB 直播買家習慣。**絕對禁止出現任何質疑、懷疑或比價的負面語氣**。所有留言都必須是正向支持、稱讚划算、期待或決定下單。
                4. 禁忌命令與代稱 (極重要)：絕對禁止生成只有「+1」、「好用」、「買了」等過於零碎、沒頭沒尾的單詞！每一則留言 (即使是短句) 都必須是【語意完整的自然句子】。同時，盡量搭配使用「這個」、「這罐」、「這組」、「這件」來代稱商品，讓語氣更自然。
                5. 稱呼限制 (極重要)：**絕對禁止在留言中使用「小編」這個詞**！如果有需要稱呼對方，請隨機使用以下稱呼：【{host_instruction}】。大約每 10 則留言出現 1 次稱呼即可 (約10%機率)，其餘 90% 留言請直接講重點，不要加任何稱呼。
                6. 留言者人設 (極重要)：請將這 {num_comments} 則留言，分配給以下這些不同身分的買家來發言：【{persona_instruction}】。請生動地模仿這些族群各自的口吻與關注點。特別注意：若是「通用 (不分性別年齡，最百搭)」人設，請確保用語絕對中性，嚴禁在留言中提及特定性別、年齡或家庭身分。
                7. 表情符號：{'絕對不要使用表情符號' if emoji_freq == 0 else f'適度使用表情符號 (活躍度 {emoji_freq}/5)'}。
                8. 標點符號排版 (極重要)：為了模仿最真實的打字習慣，請讓大約一半 (50%) 的留言維持正常的標點符號；**另一半 (50%) 的留言請「完全不要使用任何標點符號」，遇到需要停頓或斷句的地方，請直接用「空格 (半形空白)」代替**。
                9. 風格分配 (極重要)：請大約依照以下比例混搭撰寫這 {num_comments} 則留言：
                   - 渴望型 (求關注/想買/正向驚呼)：{style_desire}份
                   - 划算型 (覺得超值/直接下單/詢問組合優惠)：{style_value}份
                   - 功效型 (期待效果/覺得設計很好)：{style_effect}份
                   - 提問型 (正向詢問使用細節、口味、出貨時間等，絕無質疑語氣)：{style_question}份
                   - 反饋型 (分享過去買過的真實好用經驗、強力推薦大家買)：{style_feedback}份
                   - 互動型 (純粹跟主播打招呼、稱讚畫面/主播、或跟其他觀眾互動)：{style_interaction}份
                """
                
                if "曾經熱賣" in is_repurchase:
                    prompt += "\n10. 【特別要求：老客回購】：這款商品曾大熱賣，請在部分留言大量加入「之前買過超好用」、「這次要多囤幾組」、「終於等到了」、「上次沒搶到這次一定要買」等熱情回購語氣。"
                else:
                    prompt += "\n10. 【特別要求：初次上架】：這是新品，請在部分留言加入「想試試看」、「感覺很厲害」、「坐等介紹」、「這什麼好特別喔」等期待嘗鮮語氣。"
                
                inputs = [prompt]
                if uploaded_file is not None:
                    image_data = Image.open(uploaded_file)
                    inputs.append(image_data)
                    prompt += "\n11. 【圖片輔助】：我有附上商品圖片，請觀察圖片中的特徵、顏色、包裝或文字，把這些細節融入留言中，讓留言更真實。"

                response = model.generate_content(inputs)
                
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
            st.button("❌ 刪除此筆", key=f"del_{record['id']}", on_click=delete_record, args=(record['id'],))
            st.write(record['content'])
