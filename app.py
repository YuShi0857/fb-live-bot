import streamlit as st
import google.generativeai as genai
import json
from datetime import datetime
import uuid

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
# 初始化歷史紀錄的暫存空間
# ==========================================
if "history" not in st.session_state:
    st.session_state.history = []

st.set_page_config(page_title="FB 直播留言生成器", page_icon="🔥", layout="wide")
st.title("🔥 FB 直播留言自動生成器 (極速版)")

col1, col2 = st.columns(2)
with col1:
    product_name = st.text_input("商品名稱 (例如：大黑天唐卡、冰絲寬褲、魚油)", "魚油")
    product_info = st.text_area("產品特色/補充說明 (可選填，直接貼上廠商文案)", height=100, placeholder="例如：這款魚油無腥味、吸收率高達80%...")
    
    total_count = st.slider("要生成幾則留言？", min_value=5, max_value=30, value=10)
    emoji_freq = st.slider("表情符號頻率 (0 代表不要，其他代表大約每 N 則出現 1 次)", min_value=0, max_value=5, value=0)
    
    # 【新增】長短交錯選項
    length_option = st.selectbox(
        "字數長度要求", 
        ["長短隨機交錯 (5-50字，最自然)", "極短句 (5-15字)", "一般長度 (15-30字)", "長篇心得 (30-50字)"]
    )

with col2:
    st.write("留言風格比例設定 (系統會自動分配)")
    ratio_a = st.number_input("渴望型比例", value=10)
    ratio_b = st.number_input("划算型比例", value=10)
    ratio_c = st.number_input("功效/體驗型比例", value=80)

btn_col1, btn_col2 = st.columns([1, 5])
with btn_col1:
    generate_btn = st.button("🚀 一鍵生成留言")
with btn_col2:
    if st.button("🗑️ 清空所有紀錄"):
        st.session_state.history = []
        st.rerun()

# 4. 按下按鈕後的處理邏輯
if generate_btn:
    with st.spinner("AI 極速通靈中，請稍候..."):
        try:
            total_ratio = ratio_a + ratio_b + ratio_c
            if total_ratio == 0: total_ratio = 1 
                
            count_a = int(total_count * (ratio_a / total_ratio))
            count_b = int(total_count * (ratio_b / total_ratio))
            count_c = total_count - count_a - count_b 

            info_condition = f"請務必參考以下產品資訊來撰寫留言：\n{product_info}" if product_info else "請根據商品名稱自行推測產品功效與特色。"

            # 【速度優化】控制表情符號與字數，並要求極簡 JSON 格式
            emoji_rule = "絕對禁止使用任何表情符號。" if emoji_freq == 0 else f"請在部分留言中自然穿插 1 個表情符號。為了真實感，請控制大約每 {emoji_freq} 則留言才出現 1 個表情符號（不要每則都有）。"
            length_rule = "請將極短句(5-15字)、一般(15-30字)、長篇(30-50字)隨機交錯混合，創造最高真實感。" if "交錯" in length_option else f"每則留言請嚴格符合「{length_option}」的字數範圍。"

            prompt = f"""
            你是一個極度智能的 FB 直播互動生成器。請生成總共 {total_count} 則關於「{product_name}」的買家留言。
            【極度重要】：請以純 JSON「字串陣列 (List of strings)」格式回傳。絕對不要包含任何 JSON 屬性名稱 (keys)。不要輸出 Markdown 標記。
            格式範例：["留言一", "留言二", "留言三"]

            {info_condition}

            嚴格要求：
            1. 根據「{product_name}」自動判斷產業切換行話。
            2. 100% 正向狂熱，嚴禁疑問句。禁止出現「+1」、「+2」或訂單編號。
            3. {length_rule}
            4. {emoji_rule}
            5. 【極致多樣性】：完全沒有重複的句型或結構，隨機帶入不同買家身份與切入點。

            請精準生成以下數量與類型：
            - {count_a} 則【強烈渴望型】
            - {count_b} 則【價格划算型】
            - {count_c} 則【功效體驗型】
            """

            response = model.generate_content(prompt)
            result_text = response.text.replace("```json", "").replace("```", "").strip()
            ai_comments = json.loads(result_text) # 這次會直接拿到一個乾淨的字串列表

            # 將這次生成的結果加入歷史紀錄 (加上專屬 ID 與時間)
            current_time = datetime.now().strftime("%H:%M:%S")
            record_id = str(uuid.uuid4())
            
            st.session_state.history.insert(0, {
                "id": record_id,
                "time": current_time,
                "product": product_name,
                "comments": ai_comments
            })

        except Exception as e:
            st.error(f"詳細錯誤原因： {e}\n(若為 JSON 解析錯誤，請再點一次生成)")

# ==========================================
# 5. 顯示區塊 (左側最新，右側歷史紀錄)
# ==========================================
if st.session_state.history:
    st.divider() 
    res_col1, res_col2 = st.columns(2)
    
    with res_col1:
        st.subheader("🎉 本次生成結果 (最新鮮)")
        latest_record = st.session_state.history[0]
        st.caption(f"生成時間: {latest_record['time']} | 產品: {latest_record['product']}")
        for text in latest_record['comments']:
            st.info(text)
            
    with res_col2:
        st.subheader("🕰️ 歷史紀錄庫")
        if len(st.session_state.history) > 1:
            # 顯示除了第一筆以外的所有歷史紀錄
            for i, record in enumerate(st.session_state.history[1:]):
                # 【新增】預設收起 (expanded=False)，讓畫面乾淨，要看再點開
                with st.expander(f"🕒 {record['time']} - {record['product']} ({len(record['comments'])}則留言)", expanded=False):
                    
                    # 【新增】單筆刪除按鈕 (透過 record['id'] 精準定位)
                    if st.button(f"🗑️ 刪除此筆 ({record['time']})", key=f"del_{record['id']}"):
                        # 找出這筆資料並從列表移除
                        st.session_state.history = [item for item in st.session_state.history if item['id'] != record['id']]
                        st.rerun() # 重新整理網頁套用變更
                    
                    # 印出該筆紀錄的留言
                    for text in record['comments']:
                        st.success(text)
        else:
            st.write("目前尚無其他歷史紀錄。")
