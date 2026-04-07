import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
from apify_client import ApifyClient
import time

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Radar Điểm Rèn Luyện HCMUE", page_icon="⚡", layout="wide")

# --- LẤY API KEY TỪ SECRETS ---
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")
APIFY_TOKEN = st.secrets.get("APIFY_TOKEN", "")

genai.configure(api_key=GEMINI_KEY)

def analyze_post_with_ai(text):
    """Hàm gọi Gemini AI để nhận diện bài viết"""
    if not GEMINI_KEY:
         return False, "Chưa cấu hình Gemini API Key"
         
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
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
        result = response.text.strip().split('\n')
        
        is_drl = "ĐÚNG" in result[0].upper()
        title = result[1] if len(result) > 1 else "Sự kiện chưa có tên"
        return is_drl, title
    except Exception as e:
        return False, f"Lỗi AI: {e}"

def fetch_facebook_posts(page_url):
    """Hàm cào bài viết bằng Apify API (Qua mặt mọi lớp chặn của FB)"""
    if not APIFY_TOKEN:
        return [], "Chưa cấu hình APIFY_TOKEN"

    client = ApifyClient(APIFY_TOKEN)
    posts_data = []
    
    # Cấu hình lệnh cho con Bot Facebook Posts Scraper của Apify
    run_input = {
        "startUrls": [{"url": page_url}],
        "resultsLimit": 3, # Chỉ lấy 3 bài mới nhất mỗi trang cho nhanh
    }

    try:
        # Gọi con bot "apify/facebook-posts-scraper"
        run = client.actor("apify/facebook-posts-scraper").call(run_input=run_input)
        
        # Rút trích dữ liệu nó cào được
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            if item.get("text"):
                posts_data.append({
                    "page_url": page_url,
                    "text": item.get("text"),
                    "link": item.get("url")
                })
        
        return posts_data, "Apify quét thành công!"
    except Exception as e:
        return [], f"Lỗi Apify: {str(e)}"

# --- GIAO DIỆN CHÍNH ---
st.title("⚡ TRUNG TÂM KIỂM SOÁT ĐIỂM RÈN LUYỆN")

tab1, tab2 = st.tabs(["📡 Radar Quét Sự Kiện", "🎯 Bảng Theo Dõi Cá Nhân"])

with tab1:
    st.info("Radar sử dụng AI Gemini và nền tảng Apify để đọc hiểu các sự kiện có điểm rèn luyện.")
    st.markdown("💡 **Mẹo nhỏ:** Lưu sẵn các link Fanpage vào app Ghi chú, khi nào cần quét điểm chỉ việc Copy & Paste vào đây!")
    
    user_urls = st.text_area("Dán link Fanpage (mỗi link 1 dòng):", 
                             "https://www.facebook.com/youth.hcmue\nhttps://www.facebook.com/phongctct.hcmue",
                             height=100)
    
    if st.button("🚀 Kích hoạt Radar", type="primary"):
        urls = [url.strip() for url in user_urls.split('\n') if url.strip()]
        
        if not urls:
            st.warning("Vui lòng nhập link!")
        else:
            # Quá trình này Apify sẽ thuê Proxy dân cư để cào nên mất khoảng 30s - 1 phút
            with st.spinner("Đang phái Bot Apify đi thu thập tin tức & gọi AI phân tích. Quá trình này mất khoảng 30s - 1 phút..."):
                all_found_posts = []
                debug_logs = {}
                
                for url in urls:
                    raw_posts, debug_text = fetch_facebook_posts(url)
                    debug_logs[url] = {"log": debug_text, "posts_found": len(raw_posts)}
                    
                    for post in raw_posts:
                        is_drl, title = analyze_post_with_ai(post["text"])
                        if is_drl:
                            post["title"] = title
                            all_found_posts.append(post)
                
                # Bảng Debug
                with st.expander("🛠️ Chẩn đoán Bot (Bấm vào để xem Bot làm việc)"):
                    for url, log in debug_logs.items():
                        st.markdown(f"**URL:** {url}")
                        st.markdown(f"**Số bài viết bắt được:** {log['posts_found']}")
                        st.markdown(f"**Trạng thái:** {log['log']}")
                        st.markdown("---")

                if len(all_found_posts) > 0:
                    st.success(f"Ting ting! Tìm thấy {len(all_found_posts)} sự kiện nóng hổi!")
                    for idx, post in enumerate(all_found_posts):
                        with st.container(border=True):
                            st.subheader(f"🔥 {post['title']}")
                            st.write(post['text'][:250] + "...")
                            st.link_button("Đến bài đăng gốc ➡️", post['link'])
                else:
                    st.warning("Tìm thấy 0 sự kiện! (Hoặc Fanpage chưa có sự kiện mới, hoặc cấu hình bị lỗi).")

with tab2:
    try:
        with open("tracker.html", "r", encoding="utf-8") as f:
            components.html(f.read(), height=1000, scrolling=True)
    except FileNotFoundError:
        st.error("Không tìm thấy file tracker.html.")
