import os
import requests
from requests.adapters import HTTPAdapter
from concurrent.futures import ThreadPoolExecutor

# --- CẤU HÌNH TỐI ƯU TỐC ĐỘ QUÉT ĐA LUỒNG ---
STREAM_TIMEOUT = 1.5  # Bỏ qua nhanh các link chết sau 1.5 giây
MAX_RETRIES = 1       # Thử lại tối đa 1 lần để tiết kiệm thời gian
USER_AGENT_TV = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Đường dẫn đọc file trực tiếp từ ổ cứng
LOCAL_M3U_PATH = "xem_football_folder/All_CHANNEL.m3u"
OUTPUT_M3U_PATH = "TVlive.m3u"

def is_working_stream(url: str) -> bool:
    """Kiểm tra phản hồi của link stream (Chỉ tập trung check HTTP Status)"""
    if not url: 
        return False
        
    # Lọc nhanh các định dạng link không hợp lệ trước khi gửi request
    valid_extensions = [".m3u8", ".flv", ".ts", ".mpd", ".index"]
    if not any(ext in url.lower() for ext in valid_extensions) and "?" not in url:
        return False

    session = requests.Session()
    adapter = HTTPAdapter(max_retries=MAX_RETRIES)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    check_headers = {
        "User-Agent": USER_AGENT_TV, 
        "Accept": "*/*", 
        "Connection": "close"
    }
    
    try:
        # Sử dụng phương thức HEAD để kiểm tra nhanh phản hồi từ server
        response = session.head(url, headers=check_headers, timeout=STREAM_TIMEOUT, allow_redirects=True)
        if response.status_code in [200, 206, 301, 302]: 
            return True
            
        # Xử lý các server chặn HEAD (trả về lỗi 403 hoặc 405), thử lại bằng GET với Range giới hạn
        if response.status_code in [403, 405]:
            check_headers["Range"] = "bytes=0-1024"
            res_get = session.get(url, headers=check_headers, timeout=STREAM_TIMEOUT, stream=True)
            return res_get.status_code in [200, 206]
            
        return False
    except Exception: 
        return False

def parse_m3u_from_text(text_content: str) -> list:
    """Bóc tách cấu trúc file M3U thành danh sách dictionary chứa EXTINF và URL"""
    items = []
    lines = text_content.splitlines()
    current_item = {}
    
    for line in lines:
        line = line.strip()
        if not line: 
            continue
        if line.startswith("#EXTINF:"):
            current_item = {"extinf_line": line, "url": ""}
            items.append(current_item)
        elif line.startswith("http://") or line.startswith("https://"):
            if items and items[-1]["url"] == "":
                items[-1]["url"] = line
                
    # Chỉ giữ lại các mục có đầy đủ URL
    return [i for i in items if i["url"]]

def main():
    print(f"[INFO] Bắt đầu đọc file: {LOCAL_M3U_PATH}")
    
    if not os.path.exists(LOCAL_M3U_PATH):
        print(f"[ERROR] Không tìm thấy file tại đường dẫn: {LOCAL_M3U_PATH}")
        return

    try:
        with open(LOCAL_M3U_PATH, "r", encoding="utf-8") as f:
            text_content = f.read()
        raw_data = parse_m3u_from_text(text_content)
    except Exception as e:
        print(f"[ERROR] Không thể đọc file M3U: {e}")
        return

    if not raw_data:
        print("[WARN] Dữ liệu kênh trống hoặc sai định dạng M3U.")
        return

    total_channels = len(raw_data)
    print(f"[INFO] Tìm thấy {total_channels} kênh hợp lệ. Bắt đầu kiểm tra với 60 luồng...")
    
    # Kích hoạt đa luồng kiểm tra trạng thái link
    with ThreadPoolExecutor(max_workers=60) as executor:
        future_to_item = {executor.submit(is_working_stream, item["url"]): item for item in raw_data}
        
        for future in future_to_item:
            item = future_to_item[future]
            try:
                item["is_alive"] = future.result()
            except Exception:
                item["is_alive"] = False

    # Xuất file kết quả theo đúng thứ tự ban đầu
    tv_content = "#EXTM3U\n"
    live_count = 0
    
    for item in raw_data:
        if item.get("is_alive"):
            tv_content += f"{item['extinf_line']}\n{item['url']}\n"
            live_count += 1
            
    with open(OUTPUT_M3U_PATH, "w", encoding="utf-8") as f:
        f.write(tv_content)

    print("-" * 50)
    print(f"[SUCCESS] Hoàn thành quy trình!")
    print(f"[SUCCESS] Kết quả đã lưu vào file: {OUTPUT_M3U_PATH}")
    print(f"[SUCCESS] Thống kê: {live_count}/{total_channels} kênh hoạt động tốt.")

if __name__ == "__main__":
    main()
