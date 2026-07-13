# -*- coding: utf-8 -*-
"""channels.json のYouTubeチャンネルRSSから docs/videos.json を生成"""
import json, re
from datetime import datetime, timezone
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

with open("crawler/channels.json", encoding="utf-8") as f:
    channels = json.load(f)

items = []
for ch in channels:
    url = "https://www.youtube.com/feeds/videos.xml?channel_id=" + ch["id"]
    try:
        r = requests.get(url, headers=UA, timeout=15)
        if r.status_code != 200:
            print(f"[skip] {ch['name']} : status {r.status_code}")
            continue
        entries = re.findall(r"<entry>(.*?)</entry>", r.text, re.S)
        for e in entries:
            vid = re.search(r"<yt:videoId>([^<]+)</yt:videoId>", e)
            title = re.search(r"<title>([^<]*)</title>", e)
            pub = re.search(r"<published>([^<]+)</published>", e)
            if not (vid and title):
                continue
            items.append({
                "id": vid.group(1),
                "title": title.group(1),
                "date": pub.group(1) if pub else "",
                "channel": ch["name"],
                "city": ch["city"],
            })
        print(f"[OK] {ch['name']} : {len(entries)}件")
    except Exception as ex:
        print(f"[error] {ch['name']} : {ex}")

items.sort(key=lambda x: x["date"], reverse=True)
out = {"updated": datetime.now(timezone.utc).isoformat(), "items": items}
with open("docs/videos.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"\n合計{len(items)}本を docs/videos.json に保存しました")
