import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor

# --- CẤU HÌNH TỐI ƯU ---
STREAM_TIMEOUT = 3.5  # Tăng nhẹ lên 3.5s để giảm tỉ lệ "chết oan" do mạng lag
MAX_WORKERS = 50      # 50-60 là con số an toàn cho GitHub Actions
LOCAL_M3U_PATH = "xem_football_folder/All_CHANNEL.m3u"
OUTPUT_M3U_PATH = "TVlive.m3u"

# Tạo một Session dùng chung cho toàn bộ ứng dụng (Cực kỳ quan trọng để tăng tốc)
session = requests.Session()
retries = Retry(total=1, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
adapter = HTTPAdapter(pool_connections=MAX_WORKERS, pool_maxsize=MAX_WORKERS, max_retries=retries)
session.mount("http://", adapter)
session.mount("https://", adapter)

def is_working_stream(url: str) -> bool:
    """Kiểm tra link stream tối ưu riêng cho link proxy/IPTV"""
    if not url or not url.startswith(("http://", "https://")):
        return False
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Connection": "keep-alive",
        "Range": "bytes=0-1024" # Giới hạn data tải về để tránh nặng mạng
    }

    try:
        # Dùng thẳng GET với stream=True để bypass các server chặn HEAD
        with session.get(url, headers=headers, timeout=STREAM_TIMEOUT, stream=True, allow_redirects=True) as response:
            # Chấp nhận các mã thành công thông thường của luồng stream
            if response.status_code in [200, 206]:
                return True
            
            # Một số proxy trả về 403/405 do headers Range, thử lại GET thuần không kèm Range
            if response.status_code in [403, 405, 400]:
                headers.pop("Range", None)
                with session.get(url, headers=headers, timeout=STREAM_TIMEOUT, stream=True, allow_redirects=True) as r2:
                    return r2.status_code in [200, 206]
                    
        return False
    except Exception:
        return False

def parse_m3u(text_content: str) -> list:
    """Parse M3U thông minh hơn, giữ lại cả Group-title nếu có"""
    items = []
    lines = text_content.splitlines()
    temp_extinf = None
    
    for line in lines:
        line = line.strip()
        if not line: continue
        if line.startswith("#EXTINF:"):
            temp_extinf = line
        elif line.startswith(("http://", "https://")):
            if temp_extinf:
                items.append({"extinf": temp_extinf, "url": line})
                temp_extinf = None
    return items

def main():
    if not os.path.exists(LOCAL_M3U_PATH):
        print(f"[ERROR] Không tìm thấy file: {LOCAL_M3U_PATH}")
        return

    with open(LOCAL_M3U_PATH, "r", encoding="utf-8") as f:
        raw_items = parse_m3u(f.read())

    if not raw_items:
        print("[WARN] Không tìm thấy dữ liệu kênh.")
        return

    print(f"[INFO] Quét {len(raw_items)} kênh bằng {MAX_WORKERS} luồng...")

    # Sử dụng map để giữ đúng thứ tự ban đầu của list
    urls = [item["url"] for item in raw_items]
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(is_working_stream, urls))

    # Ghi file
    live_count = 0
    with open(OUTPUT_M3U_PATH, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for i, is_alive in enumerate(results):
            if is_alive:
                f.write(f"{raw_items[i]['extinf']}\n{raw_items[i]['url']}\n")
                live_count += 1

    print(f"{'-'*30}\n[OK] Hoàn tất! Live: {live_count}/{len(raw_items)}")

if __name__ == "__main__":
    main()
