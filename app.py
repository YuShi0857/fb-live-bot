import streamlit as st
import google.generativeai as genai
import json

# ==========================================
# 1. 設定 AI API Key 
# ==========================================
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

generation_config = {
    "temperature": 0.9, 
    "top_p": 0.95,
}
model = genai.GenerativeModel('gemini-3.6-flash', generation_config=generation_config)

# ==========================================
# 初始化歷史紀錄的暫存空間 (Session State)
# ==========================================
if "history" not in st.session_state:
    st.session_state.history = []

# 3. 網頁介面設計
st.set_page_config(page_title="FB 直播留言生成器", page_icon="🔥", layout="wide") # 【新增 layout="wide" 讓左右對照空間更大】
st.title("🔥 FB 直播留言自動生成器")

col1, col2 = st.columns(2)
with col1:
    product_name = st.text_input("商品名稱 (例如：大黑天唐卡、冰絲寬褲、魚油)", "魚油")
    product_info = st.text_area("產品特色/補充說明 (可選填，直接貼上廠商文案)", height=100, placeholder="例如：這款魚油無腥味、吸收率高達80%...")
    
    total_count = st.slider("要生成幾則留言？", min_value=5, max_value=30, value=10)
    emoji_freq = st.slider("表情符號頻率 (0 代表不要，其他代表每 N 則出現 1 次)", min_value=0, max_value=5, value=0)
    length_option = st.selectbox("字數長度要求", ["極短句 (5-15字)", "一般長度 (15-30字)", "長篇心得 (30-50字)"])

with col2:
    st.write("留言風格比例設定 (系統會自動分配)")
    ratio_a = st.number_input("渴望型比例", value=10)
    ratio_b = st.number_input("划算型比例", value=10)
    ratio_c = st.number_input("功效/體驗型比例", value=80)

# 控制區的按鈕設計
btn_col1, btn_col2 = st.columns([1, 5])
with btn_col1:
    generate_btn = st.button("🚀 一鍵生成留言")
with btn_col2:
    if st.button("🗑️ 清除歷史紀錄"):
        st.session_state.history = []
        st.rerun()

# 4. 按下按鈕後的處理邏輯
if generate_btn:
    with st.spinner("AI 正在通靈中，請稍候..."):
        try:
            total_ratio = ratio_a + ratio_b + ratio_c
            if total_ratio == 0:
                total_ratio = 1 
                
            count_a = int(total_count * (ratio_a / total_ratio))
            count_b = int(total_count * (ratio_b / total_ratio))
            count_c = total_count - count_a - count_b 

            info_condition = f"請務必參考以下產品資訊來撰寫留言：\n{product_info}" if product_info else "請根據商品名稱自行推測產品功效與特色。"

            prompt = f"""
            你是一個極度智能的 FB 直播互動生成器。請生成總共 {total_count} 則關於「{product_name}」的買家留言。
            請以純 JSON 陣列格式回傳，格式必須為：
            [
              {{
                "clean_text": "完全不含表情符號的留言內容",
                "emoji_text": "與 clean_text 內容完全相同，但在句子中間或句尾，極度自然地穿插了【剛好 1 個】表情符號"
              }}
            ]
            請不要輸出任何 Markdown 標記。

            {info_condition}

            嚴格要求：
            1. 根據「{product_name}」自動判斷產業切換行話。若無法判斷，轉為萬用信任型。
            2. 100% 正向狂熱，嚴禁疑問句。
            3. 絕對禁止出現「+1」、「+2」或訂單編號。
            4. 【字數限制】：每則留言請嚴格符合「{length_option}」的字數範圍。
            5. 【極致多樣性】：你必須確保這 {total_count} 則留言「完全沒有重複的句型或結構」。請隨機帶入不同的買家身份與切入點，確保每次生成的內容都截然不同。

            請精準生成以下數量與類型：
            - {count_a} 則【強烈渴望型】：表達立刻要入手的衝動。
            - {count_b} 則【價格划算型】：強調超值、老闆佛心。
            - {count_c} 則【功效體驗型】：必須根據上述提供的產品資訊（若有），將產品賣點轉化為真實的買家使用感受。
            """

            response = model.generate_content(prompt)
            result_text = response.text.replace("```json", "").replace("```", "").strip()
            ai_comments = json.loads(result_text)

            # 將這次生成的結果整理成一個列表
            current_batch = []
            for index, item in enumerate(ai_comments):
                if emoji_freq > 0 and (index + 1) % emoji_freq == 0:
                    final_text = item.get('emoji_text', item.get('clean_text', ''))
                else:
                    final_text = item.get('clean_text', '')
                current_batch.append(final_text)
            
            # 【關鍵】把最新產出的結果「塞到歷史紀錄的最前面」
            st.session_state.history.insert(0, current_batch)

        except Exception as e:
            st.error(f"詳細錯誤原因： {e}")

# ==========================================
# 5. 顯示區塊 (將畫面切分為左右兩邊對照)
# ==========================================
if st.session_state.history:
    st.divider() # 畫一條分隔線
    res_col1, res_col2 = st.columns(2)
    
    with res_col1:
        st.subheader("🎉 本次生成結果 (最新)")
        # 顯示歷史紀錄的第一筆 (也就是最新鮮剛出爐的)
        for text in st.session_state.history[0]:
            st.info(text)
            
    with res_col2:
        st.subheader("🕰️ 歷史紀錄 (前次生成)")
        if len(st.session_state.history) > 1:
            # 將過去的紀錄用折疊面板 (expander) 包起來，畫面比較乾淨
            for i, batch in enumerate(st.session_state.history[1:]):
                with st.expander(f"歷史紀錄 {i+1} (點擊展開比對)", expanded=(i==0)):
                    for text in batch:
                        st.success(text) # 用不同顏色(綠色)區分歷史紀錄
        else:
            st.write("目前尚無歷史紀錄，請再按一次生成按鈕。")