import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
from playwright.sync_api import sync_playwright
import time
import os

# --- MẸO CHO STREAMLIT CLOUD ---
# Lệnh này ép Streamlit Cloud tải trình duyệt ảo về để Playwright có thể chạy
os.system("playwright install chromium")

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Radar Điểm Rèn Luyện HCMUE", page_icon="⚡", layout="wide")

# --- CẤU HÌNH GEMINI API ---
# Bạn cần lấy API Key miễn phí từ Google AI Studio và điền vào đây
# Gợi ý: Trên Streamlit Cloud, nên lưu API_KEY vào phần Settings -> Secrets
API_KEY = st.secrets.get("GEMINI_API_KEY", "ĐIỀN_API_KEY_CỦA_BẠN_VÀO_ĐÂY_NẾU_CHẠY_LOCAL")
genai.configure(api_key=API_KEY)

def analyze_post_with_ai(text):
    """Hàm gọi Gemini AI để nhận diện bài viết có điểm rèn luyện không"""
    if not API_KEY or API_KEY == "ĐIỀN_API_KEY_CỦA_BẠN_VÀO_ĐÂY_NẾU_CHẠY_LOCAL":
         return True, "Chưa cấu hình API Key, hiển thị tạm."
         
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Bạn là trợ lý cho sinh viên. Hãy đọc bài đăng Facebook sau đây của tổ chức Đoàn/Hội.
        Xác định xem bài viết này CÓ PHẢI là một sự kiện, hội thảo, cuộc thi, hoặc hoạt động tình nguyện mà sinh viên tham gia có thể được cộng "điểm rèn luyện" hay không?
        
        Trả lời theo định dạng sau (chỉ trả lời 2 dòng, không thêm gì khác):
        Dòng 1: ĐÚNG hoặc SAI
        Dòng 2: Tóm tắt tên sự kiện đó trong 1 câu ngắn gọn.
        
        Nội dung bài viết:
        "{text[:1000]}"
        """
        response = model.generate_content(prompt)
        result = response.text.strip().split('\n')
        
        is_drl = "ĐÚNG" in result[0].upper()
        title = result[1] if len(result) > 1 else text[:50] + "..."
        return is_drl, title
    except Exception as e:
        return False, "Lỗi AI"

def fetch_facebook_posts(page_url):
    """Hàm cào bài viết và LINK bằng Playwright"""
    posts_data = []
    
    # Mẹo: Dùng m.facebook.com (giao diện mobile) dễ cào và ít bị chặn hơn www
    mobile_url = page_url.replace("www.facebook.com", "m.facebook.com")
    
    with sync_playwright() as p:
        # Chạy ẩn danh, không mở UI
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
        )
        page = context.new_page()
        
        try:
            page.goto(mobile_url, timeout=60000)
            page.wait_for_timeout(3000) # Chờ FB load JS
            
            # Cuộn xuống một chút để FB tải thêm bài
            page.evaluate("window.scrollBy(0, 2000)")
            page.wait_for_timeout(2000)

            # Tìm các thẻ chứa bài viết (Trên m.facebook, thường nằm trong <article> hoặc div có data-ft)
            # Ở đây ta bắt các thẻ a có chứa link '/story.php' hoặc '/posts/' để tóm link
            links = page.locator("a[href*='/story.php'], a[href*='/posts/'], a[href*='/photos/']").all()
            
            # Lấy tối đa 5 link bài mới nhất để tránh AI bị quá tải
            seen_texts = set()
            for link in links[:15]:
                href = link.get_attribute("href")
                
                # Sửa link mobile thành link desktop cho sinh viên dễ xem
                if href and href.startswith("/"):
                    full_link = "https://www.facebook.com" + href
                else:
                    full_link = href
                
                # Lấy nội dung text của thẻ cha chứa link đó
                parent_element = link.locator("xpath=..")
                text_content = parent_element.inner_text().strip()
                
                if text_content and len(text_content) > 50 and text_content not in seen_texts:
                    seen_texts.add(text_content)
                    posts_data.append({
                        "page_url": page_url,
                        "text": text_content,
                        "link": full_link
                    })
                
                if len(posts_data) >= 3: # Chỉ lấy 3 bài mới nhất mỗi trang
                    break
                    
        except Exception as e:
            st.error(f"Lỗi khi quét {page_url}: {e}")
        finally:
            browser.close()
            
    return posts_data

# --- GIAO DIỆN CHÍNH ---
st.title("⚡ TRUNG TÂM KIỂM SOÁT ĐIỂM RÈN LUYỆN")

tab1, tab2 = st.tabs(["📡 Radar Quét Sự Kiện", "🎯 Bảng Theo Dõi Cá Nhân"])

# ==========================================
# TAB 1: RADAR QUÉT SỰ KIỆN (Dùng Python)
# ==========================================
with tab1:
    st.info("Radar sử dụng AI Gemini để đọc hiểu và lọc các sự kiện có điểm rèn luyện.")
    
    # Dòng ghi chú nhắc nhở tinh tế
    st.markdown("💡 **Mẹo nhỏ:** Bạn hãy lưu sẵn các link Fanpage quan tâm vào app Ghi chú (Note) hoặc Zalo Truyền file, khi nào cần quét điểm chỉ việc Copy & Paste vào đây cho lẹ nhé!")
    
    user_urls = st.text_area("Dán link Fanpage (mỗi link 1 dòng):", 
                             "https://www.facebook.com/DoanHoiVatLyHCMUE\nhttps://www.facebook.com/TuoiTreHCMUE", 
                             height=100)
    
    if st.button("🚀 Kích hoạt Radar", type="primary"):
        urls = [url.strip() for url in user_urls.split('\n') if url.strip()]
        
        if not urls:
            st.warning("Vui lòng nhập link!")
        else:
            with st.spinner("Đang điều khiển trình duyệt ẩn danh cào dữ liệu & gọi AI phân tích. Quá trình này mất khoảng 15-30 giây..."):
                all_found_posts = []
                
                # Quét từng page
                for url in urls:
                    raw_posts = fetch_facebook_posts(url)
                    for post in raw_posts:
                        # Gửi cho AI check
                        is_drl, title = analyze_post_with_ai(post["text"])
                        if is_drl:
                            post["title"] = title
                            all_found_posts.append(post)
                
                st.success(f"Ting ting! Tìm thấy {len(all_found_posts)} sự kiện nóng hổi!")
                
                # Hiển thị kết quả có LINK THẬT
                for idx, post in enumerate(all_found_posts):
                    with st.container(border=True):
                        st.subheader(f"🔥 {post['title']}")
                        st.write(post['text'][:200] + "...")
                        st.link_button("Đến bài viết gốc trên Facebook ➡️", post['link'])
with tab2:
    try:
        with open("tracker.html", "r", encoding="utf-8") as f:
            components.html(f.read(), height=1000, scrolling=True)
    except FileNotFoundError:
        st.error("Không tìm thấy file tracker.html.")
