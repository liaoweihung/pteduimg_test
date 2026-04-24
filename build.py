import datetime
import fnmatch
import json
import os
import re
from pathlib import Path

IMG_DIR = Path('img')
MANUAL_FILE = Path('cards.manual.json')
CARDS_FILE = Path('cards.json')
IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.webp'}

CATEGORY_RULES = [
    ('multilingual', '🌍', ['lan_', 'lang', 'multi']),
    ('operation', '🧴', ['eye_', 'ear_', 'nasal_', 'rec_', 'vag_', 'hem_', 'mdi', 'susp', 'syrup', 'pos', 'augmentin', 'zithromax']),
    ('drug', '💊', ['ntg', 'neupro', 'lidopat', 'nicotine']),
    ('life', '🩹', ['wound', 'scar', 'wrap', 'dm_', 'hair', 'fall', 'damage', 'wash'])
]

TITLE_WORDS = {
    'eye': '眼藥膏', 'ear': '耳滴劑', 'nasal': '鼻噴劑', 'rec': '肛門塞劑',
    'vag': '陰道塞劑', 'hem_oint': '痔瘡軟膏(內)', 'mdi': 'MDI 吸入器',
    'ntg': 'NTG 舌下錠', 'lan': '多語服藥時間', 'dm_damage': '長期高血糖的危害'
}

def load_manual():
    if MANUAL_FILE.exists():
        return json.loads(MANUAL_FILE.read_text(encoding='utf-8'))
    return {}

def list_images():
    if not IMG_DIR.exists():
        return []
    return sorted([p.name for p in IMG_DIR.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS], key=natural_key)

def natural_key(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]

def strip_number_suffix(stem):
    return re.sub(r'[_-]?\d+$', '', stem)

def infer_key(filename):
    stem = Path(filename).stem
    lower = stem.lower()
    if lower.startswith('ped_abx_susp'):
        return 'Ped_abx_susp'
    if lower.startswith('augmentin'):
        return 'Ped_susp'
    if lower.startswith('zithromax'):
        return 'ZithromaxPOS'
    if lower.startswith('ps_hair'):
        return 'hair_wash'
    return strip_number_suffix(stem)

def infer_meta(key, files):
    joined = ' '.join([key] + files).lower()
    category, icon = 'uncategorized', '📌'
    for cat, ic, needles in CATEGORY_RULES:
        if any(n in joined for n in needles):
            category, icon = cat, ic
            break
    title_key = key.lower()
    title = TITLE_WORDS.get(title_key, key.replace('_', ' '))
    return {'category': category, 'title': title, 'icon': icon, 'order': 999}

def match_manual_patterns(manual, images):
    assigned = {}
    used = set()
    for key, meta in manual.items():
        patterns = meta.get('patterns')
        if not patterns:
            continue
        matched = []
        for pat in patterns:
            matched.extend([img for img in images if fnmatch.fnmatch(img, pat)])
        matched = sorted(set(matched), key=natural_key)
        if matched:
            assigned[key] = matched
            used.update(matched)
    return assigned, used

def build_cards():
    manual = load_manual()
    images = list_images()
    cards, used = match_manual_patterns(manual, images)

    for img in images:
        if img in used:
            continue
        key = infer_key(img)
        cards.setdefault(key, []).append(img)

    data = {}
    for key, files in sorted(cards.items(), key=lambda kv: natural_key(kv[0])):
        meta = infer_meta(key, files)
        meta.update({k: v for k, v in manual.get(key, {}).items() if k != 'patterns'})
        meta['steps'] = [f'img/{f}' for f in sorted(files, key=natural_key)]
        # 避免 texts 長度超過實際圖片數造成空白；不足時前端會顯示預設提示
        if 'texts' in meta:
            meta['texts'] = meta['texts'][:len(meta['steps'])]
        data[key] = meta

    CARDS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'✅ cards.json 已更新，共 {len(data)} 組圖卡、{sum(len(v["steps"]) for v in data.values())} 張圖片')
    return data

def update_service_worker(data):
    sw_path = Path('sw.js')
    if not sw_path.exists():
        print('⚠️ 找不到 sw.js，略過 PWA 快取更新')
        return

    cache_list = ["'./'", "'./index.html'", "'./cards.json'", "'./manifest.json'", "'./icon.png'"]
    for item in data.values():
        for img_path in item['steps']:
            cache_list.append(f"'./{img_path}'")
    cache_array_str = ",\n  ".join(dict.fromkeys(cache_list))

    new_version = f"pwa-cache-v{datetime.datetime.now().strftime('%Y%m%d%H%M')}"
    sw_content = sw_path.read_text(encoding='utf-8')
    sw_content = re.sub(r"const CACHE_NAME = '.*?';", f"const CACHE_NAME = '{new_version}';", sw_content)
    sw_content = re.sub(r"const urlsToCache = \[.*?\];", f"const urlsToCache = [\n  {cache_array_str}\n];", sw_content, flags=re.DOTALL)
    sw_path.write_text(sw_content, encoding='utf-8')
    print(f'✅ sw.js 已更新版本：{new_version}')

def update_sitemap():
    today_str = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    sitemap_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://liaoweihung.github.io/pteduimg/</loc>
    <lastmod>{today_str}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>'''
    Path('sitemap.xml').write_text(sitemap_content, encoding='utf-8')
    print(f'✅ sitemap.xml 已更新：{today_str}')

if __name__ == '__main__':
    data = build_cards()
    update_service_worker(data)
    update_sitemap()
