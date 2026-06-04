import os
import re
import requests
from requests.adapters import HTTPAdapter
from concurrent.futures import ThreadPoolExecutor

STREAM_TIMEOUT = 4.5
MAX_RETRIES = 2
USER_AGENT_TV = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ĐƯỜNG DẪN ĐẾN FILE RAW TRÊN KHO XEM_FOOTBALL CÔNG KHAI CỦA BẠN
RAW_M3U_URL = "https://raw.githubusercontent.com/huybuonvp/xem_football/main/All_CHANNEL.m3u"

def is_working_stream(url: str) -> bool:
    if not url: return False
    if "bongda.m3u" in url or "pub-26bab83910ab" in url or "luongsontv" in url: 
        return True
    if not any(ext in url.lower() for ext in [".m3u8", ".flv", ".ts", ".mpd", ".index"]) and "?" not in url:
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
    except Exception: return False

def parse_m3u_from_text(text_content):
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
    print(f"Đang tải file All_CHANNEL.m3u từ kho xem_football...")
    try:
        response = requests.get(RAW_M3U_URL, timeout=10)
        if response.status_code != 200:
            print("Không thể tải file từ kho xem_football.")
            return
        raw_data = parse_m3u_from_text(response.text)
    except Exception as e:
        print(f"Lỗi kết nối mạng: {e}")
        return

    if not raw_data:
        print("Dữ liệu kênh thô trống rỗng.")
        return

    print(f"Bắt đầu kiểm tra trạng thái {len(raw_data)} kênh...")
    alive_items = []
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {executor.submit(is_working_stream, item["url"]): item for item in raw_data}
        for future in futures:
            item = futures[future]
            if future.result(): alive_items.append(item)

    # --- TẠO FILE TVLIVE.M3U SẠCH SẼ ---
    tv_content = "#EXTM3U\n"
    count = 0
    for item in alive_items:
        if any(ext in item["url"].lower() for ext in [".m3u8", ".flv"]):
            tv_content += item["extinf_line"] + "\n" + item["url"] + "\n"
            count += 1
            
    with open("TVlive.m3u", "w", encoding="utf-8") as f:
        f.write(tv_content)

    print(f"Thành công! Đã lưu file TVlive.m3u sạch ({count} kênh) vào kho xembongda.")

if __name__ == "__main__":
    main()
