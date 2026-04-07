import streamlit as st
import streamlit.components.v1 as components
import time

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Hệ Sinh Thái Điểm Rèn Luyện", page_icon="⚡", layout="wide")
st.title("⚡ TRUNG TÂM KIỂM SOÁT ĐIỂM RÈN LUYỆN HCMUE")

# --- CHIA TAB GIAO DIỆN ---
tab1, tab2 = st.tabs(["📡 Radar Quét Sự Kiện", "🎯 Bảng Theo Dõi Cá Nhân"])

# ==========================================
# TAB 1: RADAR QUÉT SỰ KIỆN (Dùng Python)
# ==========================================
with tab1:
    st.markdown("### 📡 Tự động tìm kiếm cơ hội kiếm điểm")
    st.info("Nhập link Fanpage công khai của Đoàn - Hội. Trí tuệ nhân tạo sẽ tự động đọc và lọc ra các sự kiện có thể tham gia lấy điểm rèn luyện.")
    
    user_urls = st.text_area("Dán link Fanpage (mỗi link 1 dòng):", 
                             "https://www.facebook.com/DoanHoiToanHocHCMUE\nhttps://www.facebook.com/DoanHoiVatLyHCMUE")
    
    if st.button("🚀 Kích hoạt Radar", type="primary"):
        urls = [url.strip() for url in user_urls.split('\n') if url.strip()]
        
        if not urls:
            st.warning("Vui lòng nhập ít nhất 1 link!")
        else:
            with st.spinner("Đang điều khiển trình duyệt ẩn danh cào dữ liệu & gọi AI phân tích..."):
                # --- CHỖ NÀY SẼ ĐIỀN CODE PLAYWRIGHT & GEMINI Ở BƯỚC SAU ---
                time.sleep(2) # Chờ giả lập
                st.success("Đã tìm thấy 2 sự kiện mới!")
                
                # Hiển thị kết quả giả lập
                st.write("**1. Tọa đàm Kỹ năng Sư phạm** (Nguồn: Khoa Vật Lý)")
                st.write("**2. Tuyển CTV Mùa hè xanh** (Nguồn: Khoa Toán)")

# ==========================================
# TAB 2: TRACKER CÁ NHÂN (Nhúng HTML/JS)
# ==========================================
with tab2:
    st.markdown("### 🎯 Quản lý tiến độ & Lưu minh chứng")
    # Đọc file HTML đã làm và nhúng vào Streamlit
    try:
        with open("tracker.html", "r", encoding="utf-8") as f:
            html_content = f.read()
            # Chiều cao set 1000px, có thanh cuộn để bao trọn giao diện
            components.html(html_content, height=1000, scrolling=True)
    except FileNotFoundError:
        st.error("Không tìm thấy file tracker.html. Hãy đảm bảo file này nằm cùng thư mục với app.py")
