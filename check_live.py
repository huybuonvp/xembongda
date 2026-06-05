import os
import hashlib
import requests
from requests.adapters import HTTPAdapter
from concurrent.futures import ThreadPoolExecutor

# --- CẤU HÌNH TỐI ƯU TỐC ĐỘ QUÉT ĐA LUỒNG ---
STREAM_TIMEOUT = 1.5
MAX_RETRIES = 1
USER_AGENT_TV = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

LOCAL_M3U_PATH = "xem_football_folder/All_CHANNEL.m3u"
OUTPUT_M3U_PATH = "TVlive.m3u"
HASH_CACHE_PATH = "file_hash.txt"  # File lưu dấu vân tay của All_CHANNEL.m3u

def get_file_md5(file_path: str) -> str:
    """Hàm tính mã MD5 (dấu vân tay) của file để nhận diện thay đổi nội dung"""
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def is_working_stream(url: str) -> bool:
    if not url: return False
    valid_extensions = [".m3u8", ".flv", ".ts", ".mpd", ".index"]
    if not any(ext in url.lower() for ext in valid_extensions) and "?" not in url:
        return False

    session = requests.Session()
    adapter = HTTPAdapter(max_retries=MAX_RETRIES)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    check_headers = {"User-Agent": USER_AGENT_TV, "Accept": "*/*", "Connection": "close"}
    
    try:
        response = session.head(url, headers=check_headers, timeout=STREAM_TIMEOUT, allow_redirects=True)
        if response.status_code in [200, 206, 301, 302]: return True
        if response.status_code in [403, 405]:
            check_headers["Range"] = "bytes=0-1024"
            res_get = session.get(url, headers=check_headers, timeout=STREAM_TIMEOUT, stream=True)
            return res_get.status_code in [200, 206]
        return False
    except Exception: 
        return False

def parse_m3u_from_text(text_content: str) -> list:
    items = []
    lines = text_content.splitlines()
    current_item = {}
    for line in lines:
        line = line.strip()
        if not line: continue
        if line.startswith("#EXTINF:"):
            current_item = {"extinf_line": line, "url": ""}
            items.append(current_item)
        elif line.startswith("http://") or line.startswith("https://"):
            if items and items[-1]["url"] == "":
                items[-1]["url"] = line
    return [i for i in items if i["url"]]

def main():
    print(f"[INFO] Bắt đầu kiểm tra file: {LOCAL_M3U_PATH}")
    
    if not os.path.exists(LOCAL_M3U_PATH):
        print(f"[ERROR] Không tìm thấy file tại đường dẫn: {LOCAL_M3U_PATH}")
        return

    # --- BƯỚC KIỂM TRA THAY ĐỔI FILE ---
    current_hash = get_file_md5(LOCAL_M3U_PATH)
    
    if os.path.exists(HASH_CACHE_PATH):
        with open(HASH_CACHE_PATH, "r", encoding="utf-8") as f:
            old_hash = f.read().strip()
        
        if current_hash == old_hash:
            print("[INFO] KHÔNG CÓ THAY ĐỔI: File All_CHANNEL.m3u giống hệt lần chạy trước.")
            print("[INFO] Bỏ qua quy trình check live để tiết kiệm thời gian.")
            return
        else:
            print("[⚡ PHÁT HIỆN] File All_CHANNEL.m3u ĐÃ ĐƯỢC CẬP NHẬT MỚI! Tiến hành quét...")
    else:
        print("[INFO] Chạy lần đầu tiên, tiến hành quét toàn bộ file...")

    # --- TIẾN HÀNH ĐỌC VÀ QUÉT FILE KHI CÓ THAY ĐỔI ---
    try:
        with open(LOCAL_M3U_PATH, "r", encoding="utf-8") as f:
            text_content = f.read()
        raw_data = parse_m3u_from_text(text_content)
    except Exception as e:
        print(f"[ERROR] Không thể đọc file M3U: {e}")
        return

    if not raw_data:
        print("[WARN] Dữ liệu kênh trống.")
        return

    total_channels = len(raw_data)
    print(f"[INFO] Tìm thấy {total_channels} kênh. Bắt đầu check live (60 luồng)...")
    
    with ThreadPoolExecutor(max_workers=60) as executor:
        future_to_item = {executor.submit(is_working_stream, item["url"]): item for item in raw_data}
        for future in future_to_item:
            item = future_to_item[future]
            try:
                item["is_alive"] = future.result()
            except Exception:
                item["is_alive"] = False

    # Xuất file TVlive.m3u
    tv_content = "#EXTM3U\n"
    live_count = 0
    for item in raw_data:
        if item.get("is_alive"):
            tv_content += f"{item['extinf_line']}\n{item['url']}\n"
            live_count += 1
            
    with open(OUTPUT_M3U_PATH, "w", encoding="utf-8") as f:
        f.write(tv_content)

    # LƯU LẠI MÃ HASH MỚI SAU KHI QUÉT THÀNH CÔNG
    with open(HASH_CACHE_PATH, "w", encoding="utf-8") as f:
        f.write(current_hash)

    print("-" * 50)
    print(f"[SUCCESS] Hoàn thành! Đã lọc {live_count}/{total_channels} kênh live.")
    print(f"[SUCCESS] Đã cập nhật lịch sử lưu vết file mới.")

if __name__ == "__main__":
    main()
