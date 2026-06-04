import os
import re
import requests
from requests.adapters import HTTPAdapter
from concurrent.futures import ThreadPoolExecutor

# --- CẤU HÌNH TỐI ƯU TỐC ĐỘ QUÉT ĐA LUỒNG ---
STREAM_TIMEOUT = 1.5  # Hạ xuống 1.5 giây để bỏ qua nhanh các link chết hẳn
MAX_RETRIES = 1       # Thử lại 1 lần duy nhất để tiết kiệm thời gian
USER_AGENT_TV = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Đường dẫn đọc file trực tiếp trên ổ cứng máy chủ ảo sau khi Checkout
LOCAL_M3U_PATH = "xem_football_folder/All_CHANNEL.m3u"

def is_working_stream(url: str) -> bool:
    if not url: return False
    # Ưu tiên các link đặc biệt chạy thẳng không cần check để tăng tốc
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
    except Exception: 
        return False

def parse_m3u_from_text(text_content):
    """Bóc tách cấu trúc file M3U từ văn bản thành danh sách dạng mảng"""
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
    print(f"[INFO] Bắt đầu đọc file thô trực tiếp từ ổ cứng: {LOCAL_M3U_PATH}")
    
    if not os.path.exists(LOCAL_M3U_PATH):
        print(f"[ERROR] Không tìm thấy file tại đường dẫn: {LOCAL_M3U_PATH}")
        return

    try:
        with open(LOCAL_M3U_PATH, "r", encoding="utf-8") as f:
            text_content = f.read()
        raw_data = parse_m3u_from_text(text_content)
    except Exception as e:
        print(f"[ERROR] Không thể đọc file M3U cục bộ: {e}")
        return

    if not raw_data:
        print("[WARN] Dữ liệu kênh thô trống rỗng hoặc sai định dạng.")
        return

    print(f"[INFO] Tổng hợp được {len(raw_data)} kênh thô. Bắt đầu check live (60 Workers)...")
    
    # 1. KÍCH HOẠT KIỂM TRA ĐA LUỒNG SONG SONG
    with ThreadPoolExecutor(max_workers=60) as executor:
        # Ánh xạ luồng chạy ngầm vào chính đối tượng item để giữ liên kết dữ liệu
        future_to_item = {executor.submit(is_working_stream, item["url"]): item for item in raw_data}
        
        # Đợi toàn bộ các luồng trả về trạng thái sống/chết độc lập
        for future in future_to_item:
            item = future_to_item[future]
            try:
                item["is_alive"] = future.result()
            except Exception:
                item["is_alive"] = False

    # --- 2. XUẤT FILE TVLIVE.M3U SẠCH - ĐẢM BẢO GIỮ NGUYÊN 100% THỨ TỰ THEO THỜI GIAN GỐC ---
    tv_content = "#EXTM3U\n"
    count = 0
    
    # Duyệt tuần tự từ trên xuống dưới theo mảng gốc ban đầu của file All_CHANNEL.m3u
    for item in raw_data:
        if item.get("is_alive") and any(ext in item["url"].lower() for ext in [".m3u8", ".flv"]):
            tv_content += item["extinf_line"] + "\n" + item["url"] + "\n"
            count += 1
            
    with open("TVlive.m3u", "w", encoding="utf-8") as f:
        f.write(tv_content)

    print(f"[SUCCESS] Hoàn thành quy trình! Đã giữ nguyên cấu trúc thời gian ban đầu.")
    print(f"[SUCCESS] Đã lọc được {count}/{len(raw_data)} kênh sống và lưu vào TVlive.m3u.")

if __name__ == "__main__":
    main()
