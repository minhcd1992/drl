import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
from playwright.sync_api import sync_playwright
import time

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Radar Điểm Rèn Luyện HCMUE", page_icon="⚡", layout="wide")

# --- CẤU HÌNH GEMINI API ---
API_KEY = st.secrets.get("GEMINI_API_KEY", "ĐIỀN_API_KEY_CỦA_BẠN_VÀO_ĐÂY_NẾU_CHẠY_LOCAL")
genai.configure(api_key=API_KEY)

def analyze_post_with_ai(text):
    """Hàm gọi Gemini AI để nhận diện bài viết"""
    if not API_KEY or API_KEY == "ĐIỀN_API_KEY_CỦA_BẠN_VÀO_ĐÂY_NẾU_CHẠY_LOCAL":
         return False, "Chưa cấu hình API Key"
         
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
    """Hàm cào bài viết và LINK bằng Playwright (Bản chống Login Wall)"""
    posts_data = []
    # Thử dùng www thay vì m.facebook vì bản web đôi khi cho phép cuộn xem bài trước khi ép đăng nhập
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/usr/bin/chromium", 
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled" # Giấu thân phận bot
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # Bật biến lưu raw text để debug
        raw_debug_text = ""
        
        try:
            page.goto(page_url, timeout=60000)
            page.wait_for_timeout(3000) 
            
            # Cố gắng tắt popup đăng nhập bằng phím Escape
            page.keyboard.press("Escape")
            page.wait_for_timeout(1000)
            
            # Cuộn xuống để tải bài
            page.evaluate("window.scrollBy(0, 1500)")
            page.wait_for_timeout(3000)

            # LƯU LẠI TOÀN BỘ TEXT MÀ BOT NHÌN THẤY ĐỂ DEBUG
            raw_debug_text = page.locator("body").inner_text()

            # Lấy tất cả các thẻ có chứa link bài viết
            links = page.locator("a[href*='/posts/'], a[href*='/photos/']").all()
            
            seen_texts = set()
            for link in links[:20]:
                href = link.get_attribute("href")
                
                # Tìm element cha bọc ngoài chứa text nội dung (đi lên 5-6 cấp tùy layout Facebook)
                parent_element = link.locator("xpath=../../../../..") 
                try:
                    text_content = parent_element.inner_text().strip()
                except:
                    continue
                
                if text_content and len(text_content) > 100 and text_content not in seen_texts:
                    seen_texts.add(text_content)
                    full_link = href if href.startswith("http") else "https://www.facebook.com" + href
                    posts_data.append({
                        "page_url": page_url,
                        "text": text_content,
                        "link": full_link.split('?')[0] # Cắt bỏ phần tracking rườm rà
                    })
                
                if len(posts_data) >= 3:
                    break
                    
        except Exception as e:
            raw_debug_text = f"Lỗi Scraping: {str(e)}"
        finally:
            browser.close()
            
    return posts_data, raw_debug_text

# --- GIAO DIỆN CHÍNH ---
st.title("⚡ TRUNG TÂM KIỂM SOÁT ĐIỂM RÈN LUYỆN")

tab1, tab2 = st.tabs(["📡 Radar Quét Sự Kiện", "🎯 Bảng Theo Dõi Cá Nhân"])

with tab1:
    st.info("Radar sử dụng AI Gemini để đọc hiểu và lọc các sự kiện có điểm rèn luyện.")
    st.markdown("💡 **Mẹo nhỏ:** Lưu sẵn các link Fanpage vào app Ghi chú, khi nào cần quét điểm chỉ việc Copy & Paste vào đây!")
    
    user_urls = st.text_area("Dán link Fanpage (mỗi link 1 dòng):", 
                             "https://www.facebook.com/youth.hcmue\nhttps://www.facebook.com/phongctct.hcmue",
                             height=100)
    
    if st.button("🚀 Kích hoạt Radar", type="primary"):
        urls = [url.strip() for url in user_urls.split('\n') if url.strip()]
        
        if not urls:
            st.warning("Vui lòng nhập link!")
        else:
            with st.spinner("Đang cho bot cào dữ liệu & gọi AI. Vui lòng chờ..."):
                all_found_posts = []
                debug_logs = {}
                
                for url in urls:
                    raw_posts, debug_text = fetch_facebook_posts(url)
                    debug_logs[url] = {"raw_text": debug_text, "posts_found": len(raw_posts)}
                    
                    for post in raw_posts:
                        is_drl, title = analyze_post_with_ai(post["text"])
                        if is_drl:
                            post["title"] = title
                            all_found_posts.append(post)
                
                # --- PHẦN DEBUG MỚI THÊM VÀO ---
                with st.expander("🛠️ Chẩn đoán Bot (Bấm vào để xem Bot thấy gì)"):
                    for url, log in debug_logs.items():
                        st.markdown(f"**URL:** {url}")
                        st.markdown(f"**Số block bài viết bắt được:** {log['posts_found']}")
                        st.text_area("Text thô mà Bot đọc được từ trang này:", log['raw_text'][:2000] + "...\n(Đã cắt bớt)", height=150)
                # -------------------------------

                if len(all_found_posts) > 0:
                    st.success(f"Ting ting! Tìm thấy {len(all_found_posts)} sự kiện nóng hổi!")
                    for idx, post in enumerate(all_found_posts):
                        with st.container(border=True):
                            st.subheader(f"🔥 {post['title']}")
                            st.write(post['text'][:250] + "...")
                            st.link_button("Đến bài viết gốc trên Facebook ➡️", post['link'])
                else:
                    st.warning("Ting ting! Tìm thấy 0 sự kiện nóng hổi! Vui lòng kiểm tra mục 'Chẩn đoán Bot' ở trên.")

with tab2:
    try:
        with open("tracker.html", "r", encoding="utf-8") as f:
            components.html(f.read(), height=1000, scrolling=True)
    except FileNotFoundError:
        st.error("Không tìm thấy file tracker.html.")
