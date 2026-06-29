import os
import requests
from requests.adapters import HTTPAdapter
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

# --- CẤU HÌNH TỐI ƯU CẬP NHẬT ---
STREAM_TIMEOUT = 5.0  # Tăng lên 5s để tránh mất link phản hồi chậm (rất quan trọng với IPTV)
MAX_WORKERS = 50      # 50-60 luồng là tối ưu cho GitHub Actions
LOCAL_M3U_PATH = "xem_football_folder/All_CHANNEL.m3u"
OUTPUT_M3U_PATH = "TVlive.m3u"

session = requests.Session()
adapter = HTTPAdapter(pool_connections=MAX_WORKERS, pool_maxsize=MAX_WORKERS)
session.mount("http://", adapter)
session.mount("https://", adapter)

def is_working_stream(url: str) -> bool:
    """Kiểm tra link stream thông minh, hạn chế tối đa việc nhận diện sai"""
    if not url or not url.startswith(("http://", "https://")):
        return False
    
    # Tự động tạo Referer từ Domain của URL để qua mặt một số bộ lọc cơ bản
    parsed_url = urlparse(url)
    base_origin = f"{parsed_url.scheme}://{parsed_url.netloc}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Connection": "keep-alive",
        "Referer": base_origin,
        "Origin": base_origin
    }

    # BƯỚC 1: Thử bằng HEAD trước (Nhanh, nhẹ mạng, không tải data)
    try:
        response = session.head(url, headers=headers, timeout=STREAM_TIMEOUT, allow_redirects=True)
        if response.status_code in [200, 206]:
            return True
    except Exception:
        pass

    # BƯỚC 2: Nếu HEAD lỗi hoặc bị chặn (403, 405...), thử lại bằng GET với stream=True
    try:
        with session.get(url, headers=headers, timeout=STREAM_TIMEOUT, stream=True, allow_redirects=True) as response:
            if response.status_code in [200, 206]:
                # Ép đóng kết nối stream ngay sau khi nhận được thông số tốt để giải phóng bộ nhớ
                response.close()
                return True
    except Exception:
        pass

    return False

def parse_m3u(text_content: str) -> list:
    """Parse M3U giữ nguyên cấu trúc tivi chung"""
    items = []
    lines = text_content.splitlines()
    temp_extinf = None
    
    for line in lines:
        line = line.strip()
        if not line: 
            continue
        if line.startswith("#EXTINF:"):
            temp_extinf = line
        elif line.startswith(("http://", "https://")):
            if temp_extinf:
                items.append({"extinf": temp_extinf, "url": line})
                temp_extinf = None
            else:
                # Trường hợp file m3u lỗi thiếu dòng #EXTINF vẫn giữ lại link
                items.append({"extinf": f"#EXTINF:-1,Kênh không tên", "url": line})
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

    urls = [item["url"] for item in raw_items]
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(is_working_stream, urls))

    # Ghi file kết quả
    live_count = 0
    with open(OUTPUT_M3U_PATH, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for i, is_alive in enumerate(results):
            if is_alive:
                f.write(f"{raw_items[i]['extinf']}\n{raw_items[i]['url']}\n")
                live_count += 1

    print(f"{'-'*30}\n[OK] Hoàn tất! Giữ lại Live: {live_count}/{len(raw_items)}")

if __name__ == "__main__":
    main()import os
import requests
from requests.adapters import HTTPAdapter
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

# --- CẤU HÌNH TỐI ƯU CẬP NHẬT ---
STREAM_TIMEOUT = 5.0  # Tăng lên 5s để tránh mất link phản hồi chậm (rất quan trọng với IPTV)
MAX_WORKERS = 50      # 50-60 luồng là tối ưu cho GitHub Actions
LOCAL_M3U_PATH = "xem_football_folder/All_CHANNEL.m3u"
OUTPUT_M3U_PATH = "TVlive.m3u"

session = requests.Session()
adapter = HTTPAdapter(pool_connections=MAX_WORKERS, pool_maxsize=MAX_WORKERS)
session.mount("http://", adapter)
session.mount("https://", adapter)

def is_working_stream(url: str) -> bool:
    """Kiểm tra link stream thông minh, hạn chế tối đa việc nhận diện sai"""
    if not url or not url.startswith(("http://", "https://")):
        return False
    
    # Tự động tạo Referer từ Domain của URL để qua mặt một số bộ lọc cơ bản
    parsed_url = urlparse(url)
    base_origin = f"{parsed_url.scheme}://{parsed_url.netloc}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Connection": "keep-alive",
        "Referer": base_origin,
        "Origin": base_origin
    }

    # BƯỚC 1: Thử bằng HEAD trước (Nhanh, nhẹ mạng, không tải data)
    try:
        response = session.head(url, headers=headers, timeout=STREAM_TIMEOUT, allow_redirects=True)
        if response.status_code in [200, 206]:
            return True
    except Exception:
        pass

    # BƯỚC 2: Nếu HEAD lỗi hoặc bị chặn (403, 405...), thử lại bằng GET với stream=True
    try:
        with session.get(url, headers=headers, timeout=STREAM_TIMEOUT, stream=True, allow_redirects=True) as response:
            if response.status_code in [200, 206]:
                # Ép đóng kết nối stream ngay sau khi nhận được thông số tốt để giải phóng bộ nhớ
                response.close()
                return True
    except Exception:
        pass

    return False

def parse_m3u(text_content: str) -> list:
    """Parse M3U giữ nguyên cấu trúc tivi chung"""
    items = []
    lines = text_content.splitlines()
    temp_extinf = None
    
    for line in lines:
        line = line.strip()
        if not line: 
            continue
        if line.startswith("#EXTINF:"):
            temp_extinf = line
        elif line.startswith(("http://", "https://")):
            if temp_extinf:
                items.append({"extinf": temp_extinf, "url": line})
                temp_extinf = None
            else:
                # Trường hợp file m3u lỗi thiếu dòng #EXTINF vẫn giữ lại link
                items.append({"extinf": f"#EXTINF:-1,Kênh không tên", "url": line})
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

    urls = [item["url"] for item in raw_items]
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(is_working_stream, urls))

    # Ghi file kết quả
    live_count = 0
    with open(OUTPUT_M3U_PATH, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for i, is_alive in enumerate(results):
            if is_alive:
                f.write(f"{raw_items[i]['extinf']}\n{raw_items[i]['url']}\n")
                live_count += 1

    print(f"{'-'*30}\n[OK] Hoàn tất! Giữ lại Live: {live_count}/{len(raw_items)}")

if __name__ == "__main__":
    main()
