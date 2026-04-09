import os
import re
import datetime

def update_service_worker():
    print("啟動自動化打包助理...")

    # 1. 自動掃描 img 資料夾底下的所有圖片
    img_folder = 'img'
    image_files = [f for f in os.listdir(img_folder) if f.endswith(('.png', '.jpg', '.jpeg'))]
    
    # 建立 PWA 需要的快取清單 (包含首頁和所有圖片)
    cache_list = ["'./'", "'./index.html'"]
    for img in image_files:
        cache_list.append(f"'./img/{img}'")
    
    cache_array_str = ",\n  ".join(cache_list)

    # 2. 用目前的「年月日時分」產生一個絕對不會重複的自動版本號
    now = datetime.datetime.now()
    new_version = f"pwa-cache-v{now.strftime('%Y%m%d%H%M')}"

    # 3. 讀取目前的 sw.js
    with open('sw.js', 'r', encoding='utf-8') as file:
        sw_content = file.read()

    # 4. 利用正規表達式 (Regex) 自動替換版本號與檔案清單
    sw_content = re.sub(
        r"const CACHE_NAME = '.*?';", 
        f"const CACHE_NAME = '{new_version}';", 
        sw_content
    )
    
    sw_content = re.sub(
        r"const urlsToCache = \[.*?\];", 
        f"const urlsToCache = [\n  {cache_array_str}\n];", 
        sw_content, 
        flags=re.DOTALL
    )

    # 5. 寫回 sw.js
    with open('sw.js', 'w', encoding='utf-8') as file:
        file.write(sw_content)

    print(f"✅ 大功告成！")
    print(f"🔄 sw.js 版本號已自動更新為: {new_version}")
    print(f"📦 共自動收錄了 {len(image_files)} 張圖卡至離線大腦中！")

if __name__ == '__main__':
    update_service_worker()
