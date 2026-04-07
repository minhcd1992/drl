import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
from apify_client import ApifyClient
import time
from datetime import datetime, timedelta, timezone

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Radar Điểm Rèn Luyện HCMUE", page_icon="⚡", layout="wide")

# --- LẤY API KEY TỪ SECRETS ---
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")
APIFY_TOKEN = st.secrets.get("APIFY_TOKEN", "")

genai.configure(api_key=GEMINI_KEY)

def analyze_post_with_ai(text):
    """Hàm gọi Gemini AI để nhận diện bài viết"""
    if not GEMINI_KEY:
         return False, "Lỗi", "CHƯA CẤU HÌNH GEMINI API KEY TRONG SECRETS!"
         
    try:
        # SỬA LẠI TÊN MODEL Ở DÒNG NÀY THEO CHUẨN CỦA BẠN:
        model = genai.GenerativeModel('gemini-flash-latest')
        
        prompt = f"""
        Đọc đoạn văn bản sau cào từ Facebook Đoàn/Hội.
        Đoạn này CÓ PHẢI là một sự kiện/thông báo tuyển tình nguyện viên/hội thảo mà sinh viên tham gia có thể lấy điểm rèn luyện không?
        Chỉ trả lời 2 dòng:
        Dòng 1: ĐÚNG hoặc SAI
        Dòng 2: Tóm tắt tên sự kiện (nếu ĐÚNG), hoặc ghi 'Bỏ qua' (nếu SAI).
        
        Nội dung:
        "{text[:1000]}"
        """
        response = model.generate_content(prompt)
        ai_reply = response.text.strip()
        result = ai_reply.split('\n')
        
        is_drl = "ĐÚNG" in result[0].upper()
        title = result[1] if len(result) > 1 else "Sự kiện chưa có tên"
        
        return is_drl, title, ai_reply
    except Exception as e:
        return False, "Lỗi AI", f"Lỗi gọi Gemini API: {str(e)}"

def fetch_facebook_posts(page_url, days_limit=2):
    """Hàm cào bài viết bằng Apify và lọc theo thời gian"""
    if not APIFY_TOKEN:
        return [], "CHƯA CẤU HÌNH APIFY_TOKEN TRONG SECRETS!"

    client = ApifyClient(APIFY_TOKEN)
    posts_data = []
    
    # Nâng lên 15 bài để quét sâu hơn
    run_input = {
        "startUrls": [{"url": page_url}],
        "resultsLimit": 15,
    }

    try:
        run = client.actor("apify/facebook-posts-scraper").call(run_input=run_input)
        
        # Tính toán mốc thời gian cắt (Cutoff): Hiện tại trừ đi số ngày
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_limit)
        
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            text = item.get("text")
            date_str = item.get("date") # Apify thường trả về dạng "2026-04-07T10:00:00.000Z"
            
            if text and date_str:
                try:
                    # Chuyển đổi chuỗi thời gian của Facebook thành định dạng Date của Python
                    post_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    
                    # Chỉ lấy bài đăng MỚI HƠN mốc cutoff (ví dụ: trong 2 ngày qua)
                    if post_date >= cutoff_date:
                        posts_data.append({
                            "page_url": page_url,
                            "text": text,
                            "link": item.get("url"),
                            "date": post_date.strftime("%d/%m/%Y")
                        })
                except Exception:
                    # Nếu lỗi parse ngày thì cứ lấy vào để không bị sót
                    posts_data.append({
                        "page_url": page_url,
                        "text": text,
                        "link": item.get("url"),
                        "date": "Không rõ"
                    })
                    
        return posts_data, f"Apify đã lọc được {len(posts_data)} bài đăng trong {days_limit} ngày qua."
    except Exception as e:
        return [], f"Lỗi Apify: {str(e)}"

# --- GIAO DIỆN CHÍNH ---
st.title("⚡ TRUNG TÂM KIỂM SOÁT ĐIỂM RÈN LUYỆN")

tab1, tab2 = st.tabs(["📡 Radar Quét Sự Kiện", "🎯 Bảng Theo Dõi Cá Nhân"])

with tab1:
    st.info("Radar sử dụng AI Gemini và Apify để cào các tin tức trong vòng 2 NGÀY qua.")
    st.markdown("💡 **Mẹo nhỏ:** Lưu sẵn các link Fanpage vào app Ghi chú, khi nào cần quét điểm chỉ việc Copy & Paste vào đây!")
    
    user_urls = st.text_area("Dán link Fanpage (mỗi link 1 dòng):", 
                             "https://www.facebook.com/youth.hcmue\nhttps://www.facebook.com/phongctct.hcmue",
                             height=100)
    
    # Cho phép chọn số ngày quét
    days_to_scan = st.slider("Quét tin tức trong bao nhiêu ngày qua?", min_value=1, max_value=7, value=2)
    
    if st.button("🚀 Kích hoạt Radar", type="primary"):
        urls = [url.strip() for url in user_urls.split('\n') if url.strip()]
        
        if not urls:
            st.warning("Vui lòng nhập link!")
        else:
            with st.spinner("Đang phái Bot quét tin & nhâm nhi cafe chờ AI phân tích (để tránh quá tải). Vui lòng chờ vài phút..."):
                all_found_posts = []
                debug_logs = {}
                
                for url in urls:
                    raw_posts, debug_text = fetch_facebook_posts(url, days_limit=days_to_scan)
                    debug_logs[url] = {"log": debug_text, "posts": []}
                    
                    for post in raw_posts:
                        is_drl, title, ai_reason = analyze_post_with_ai(post["text"])
                        
                        debug_logs[url]["posts"].append({
                            "ngày": post["date"],
                            "text_trích_đoạn": post["text"][:150] + "...",
                            "phán_quyết_của_AI": ai_reason
                        })
                        
                        if is_drl:
                            post["title"] = title
                            all_found_posts.append(post)
                            
                        # MẸO SỐNG CÒN: Nghỉ 4.5 giây giữa mỗi lần hỏi AI để tránh bị Google khóa do quá tải (15 request/phút)
                        time.sleep(4.5)
                
                with st.expander("🛠️ Chẩn đoán AI (Bấm vào để xem AI đang nghĩ gì)"):
                    for url, log in debug_logs.items():
                        st.markdown(f"**📍 Nguồn:** `{url}` ({log['log']})")
                        for idx, p in enumerate(log["posts"]):
                            st.markdown(f"> **Bài {idx+1} ({p['ngày']}):** {p['text_trích_đoạn']}")
                            st.markdown(f"> **🤖 AI Trả lời:** `{p['phán_quyết_của_AI']}`")
                        st.divider()

                if len(all_found_posts) > 0:
                    st.success(f"Ting ting! Tìm thấy {len(all_found_posts)} sự kiện nóng hổi trong {days_to_scan} ngày qua!")
                    for idx, post in enumerate(all_found_posts):
                        with st.container(border=True):
                            st.subheader(f"🔥 {post['title']}")
                            st.caption(f"📅 Ngày đăng: {post['date']}")
                            st.write(post['text'][:250] + "...")
                            st.link_button("Đến bài đăng gốc ➡️", post['link'])
                else:
                    st.warning(f"Tìm thấy 0 sự kiện trong {days_to_scan} ngày qua! Vui lòng mở mục 'Chẩn đoán AI' ở trên để biết lý do.")

with tab2:
    try:
        with open("tracker.html", "r", encoding="utf-8") as f:
            components.html(f.read(), height=1000, scrolling=True)
    except FileNotFoundError:
        st.error("Không tìm thấy file tracker.html.")
