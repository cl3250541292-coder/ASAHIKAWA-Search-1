#!/usr/bin/env python3
# 旭川リアルタイム情報局 ニュース取得スクリプト(気象庁の本文つき版)
import json, re, sys, urllib.request, datetime
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET

UA = "AsahikawaRealtimeInfo/1.0 (Clark Award student project)"

def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def to_iso(dt):
    return dt.astimezone(datetime.timezone(datetime.timedelta(hours=9))).isoformat()

def parse_rss(xml_bytes, source_name, max_items=15):
    items = []
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    if channel is None:
        return items
    for it in channel.findall("item")[:max_items]:
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub = (it.findtext("pubDate") or "").strip()
        iso = ""
        if pub:
            try: iso = to_iso(parsedate_to_datetime(pub))
            except Exception: iso = ""
        if title and link:
            items.append({"title": title, "link": link, "date": iso, "source": source_name, "body": ""})
    return items

ATOM = "{http://www.w3.org/2005/Atom}"
JMA_KEEP = ["府県天気予報", "府県週間天気予報", "気象警報・注意報"]

def extract_headline(xml_bytes):
    try: root = ET.fromstring(xml_bytes)
    except Exception: return ""
    for el in root.iter():
        if el.tag.split('}')[-1] == 'Headline':
            for child in el.iter():
                if child.tag.split('}')[-1] == 'Text' and child.text and child.text.strip():
                    return child.text.strip()
    return ""

def parse_jma(xml_bytes, max_items=6):
    items = []
    root = ET.fromstring(xml_bytes)
    seen = set()
    for entry in root.findall(f"{ATOM}entry"):
        title = (entry.findtext(f"{ATOM}title") or "").strip()
        content = (entry.findtext(f"{ATOM}content") or "").strip()
        author = ""
        a = entry.find(f"{ATOM}author")
        if a is not None:
            author = (a.findtext(f"{ATOM}name") or "").strip()
        updated = (entry.findtext(f"{ATOM}updated") or "").strip()
        link_el = entry.find(f"{ATOM}link")
        link = link_el.get("href") if link_el is not None else ""
        if author != "旭川地方気象台": continue
        if not any(k in title for k in JMA_KEEP): continue
        if "上川" not in content and "上川" not in title: continue
        m = re.search(r"【([^】]+)】", content)
        disp = m.group(1) if m else title
        if disp in seen: continue
        seen.add(disp)
        iso = ""
        if updated:
            try: iso = to_iso(datetime.datetime.fromisoformat(updated.replace("Z","+00:00")))
            except Exception: iso = ""
        body = ""
        if link:
            try: body = extract_headline(fetch(link, timeout=15))
            except Exception: body = ""
        items.append({"title": disp, "link": link, "date": iso, "source": "気象庁", "body": body})
        if len(items) >= max_items: break
    return items

def main():
    all_items = []
    for url, name in [
        ("https://www.city.asahikawa.hokkaido.jp/700/news.xml", "旭川市"),
        ("https://www.atca.jp/feed/", "旭川観光協会"),
    ]:
        try:
            all_items += parse_rss(fetch(url), name)
            print(f"[OK] {name}", file=sys.stderr)
        except Exception as e:
            print(f"[NG] {name}: {e}", file=sys.stderr)
    for url in [
        "https://www.data.jma.go.jp/developer/xml/feed/regular.xml",
        "https://www.data.jma.go.jp/developer/xml/feed/extra.xml",
    ]:
        try:
            all_items += parse_jma(fetch(url))
            print(f"[OK] 気象庁 {url.split('/')[-1]}", file=sys.stderr)
        except Exception as e:
            print(f"[NG] 気象庁 {url}: {e}", file=sys.stderr)
    all_items.sort(key=lambda x: x["date"] or "", reverse=True)
    out = {"updated": to_iso(datetime.datetime.now(datetime.timezone.utc)), "items": all_items}
    with open("docs/news.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[DONE] docs/news.json に {len(all_items)} 件を保存しました")

if __name__ == "__main__":
    main()
