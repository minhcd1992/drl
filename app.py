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
    """Hàm gọi Gemini AI để nhận diện bài viết với Prompt siêu cấp"""
    if not GEMINI_KEY:
         return False, "Lỗi", "CHƯA CẤU HÌNH GEMINI API KEY TRONG SECRETS!"
         
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        
        # Mớm luật Điểm Rèn Luyện HCMUE cho AI
        prompt = f"""
        Bạn là chuyên gia phân tích dữ liệu cho sinh viên trường Đại học Sư Phạm TP.HCM (HCMUE). 
        Nhiệm vụ của bạn là đọc bài đăng Facebook và xác định xem bài viết này CÓ ĐANG MỞ FORM ĐĂNG KÝ THAM GIA sự kiện để lấy "Điểm Rèn Luyện" hoặc "Ngày Tình Nguyện" hay không.
        
        HÃY ĐÁNH GIÁ LÀ "ĐÚNG" NẾU BÀI VIẾT CÓ CÁC YẾU TỐ SAU (Dựa theo quy chế ĐRL):
        1. Có các từ khóa kêu gọi: "Tuyển Cộng tác viên (CTV)", "Tuyển Tình nguyện viên (TNV)", "Đăng ký tham gia", "Ban tổ chức".
        2. Có quyền lợi rõ ràng: "Giấy chứng nhận", "Quy đổi ngày tình nguyện", "Điểm rèn luyện", "Điểm CTXH".
        3. Thuộc các nhóm sự kiện: Hội thảo, tọa đàm, cuộc thi học thuật, hiến máu, hội thao, văn nghệ, chiến dịch Mùa hè xanh, Xuân tình nguyện...
        4. BẮT BUỘC phải có dấu hiệu đang mở đăng ký (như có Link điền form). Chú ý: Đừng bị lừa bởi các đoạn thơ hay lịch sử ở đầu bài.
        
        HÃY ĐÁNH GIÁ LÀ "SAI" VÀ LOẠI BỎ CÁC BÀI VIẾT SAU:
        - Chúc mừng sinh nhật, kỷ niệm ngày lễ (ví dụ: Kỷ niệm ngày sinh, Chúc mừng 26/3...).
        - Công bố kết quả minigame, kết quả cuộc thi, khen thưởng.
        - Thông báo nghỉ học, nộp học phí, lịch thi, cảnh báo học vụ.
        - Bài viết chia sẻ kiến thức, thơ ca thông thường mà không có link đăng ký tham gia sự kiện.
        
        Bài viết cần phân tích:
        \"\"\"{text[:2000]}\"\"\"
        
        Trả lời theo định dạng nghiêm ngặt 2 dòng:
        Dòng 1: ĐÚNG (nếu sinh viên có thể đăng ký tham gia sự kiện này) hoặc SAI (nếu không).
        Dòng 2: Tóm tắt tên sự kiện thật ngắn gọn (nếu ĐÚNG) hoặc ghi "Bỏ qua" (nếu SAI).
        """
        
        response = model.generate_content(prompt)
        ai_reply = response.text.strip()
        
        # Xử lý kết quả trả về, xóa các dòng trống nếu AI sinh dư
        result = [r.strip() for r in ai_reply.split('\n') if r.strip()]
        
        is_drl = "ĐÚNG" in result[0].upper()
        title = result[1] if len(result) > 1 else "Sự kiện chưa có tên"
        
        return is_drl, title, ai_reply
    except Exception as e:
        return False, "Lỗi AI", f"Lỗi gọi Gemini API: {str(e)}"
def fetch_facebook_posts(page_url, days_limit=2):
    """Hàm cào bài viết bằng Apify và lọc theo thời gian (Bản Fix Lỗi Ngày)"""
    if not APIFY_TOKEN:
        return [], "CHƯA CẤU HÌNH APIFY_TOKEN TRONG SECRETS!"

    client = ApifyClient(APIFY_TOKEN)
    posts_data = []
    
    run_input = {
        "startUrls": [{"url": page_url}],
        "resultsLimit": 15,
    }

    try:
        run = client.actor("apify/facebook-posts-scraper").call(run_input=run_input)
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_limit)
        raw_post_count = 0 # Đếm xem Apify cào được tổng cộng bao nhiêu bài thô
        
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            raw_post_count += 1
            text = item.get("text")
            
            # Tuyệt chiêu: Bắt mọi thể loại key lưu ngày tháng của Apify
            date_raw = item.get("time") or item.get("date") or item.get("createdAt")
            
            if text:
                if date_raw:
                    try:
                        # Đổi chuỗi ngày của Apify thành dạng Date của Python
                        post_date = datetime.fromisoformat(str(date_raw).replace("Z", "+00:00"))
                        
                        # So sánh: Nếu bài đăng nằm trong khoảng X ngày qua
                        if post_date >= cutoff_date:
                            posts_data.append({
                                "page_url": page_url,
                                "text": text,
                                "link": item.get("url"),
                                "date": post_date.strftime("%d/%m/%Y")
                            })
                    except Exception:
                        # Parse lỗi thì cứ lấy vào để không mất cơ hội của sinh viên
                        posts_data.append({
                            "page_url": page_url,
                            "text": text,
                            "link": item.get("url"),
                            "date": "Không rõ ngày"
                        })
                else:
                    # Nếu Apify không lấy được ngày thì cũng lấy bài luôn
                    posts_data.append({
                        "page_url": page_url,
                        "text": text,
                        "link": item.get("url"),
                        "date": "Không rõ ngày"
                    })
                    
        return posts_data, f"Apify cào thô {raw_post_count} bài -> Lọc được {len(posts_data)} bài mới!"
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
                
               # with st.expander("🛠️ Chẩn đoán AI (Bấm vào để xem AI đang nghĩ gì)"):
               #     for url, log in debug_logs.items():
               #         st.markdown(f"**📍 Nguồn:** `{url}` ({log['log']})")
               #         for idx, p in enumerate(log["posts"]):
               #             st.markdown(f"> **Bài {idx+1} ({p['ngày']}):** {p['text_trích_đoạn']}")
               #             st.markdown(f"> **🤖 AI Trả lời:** `{p['phán_quyết_của_AI']}`")
               #        st.divider()

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
