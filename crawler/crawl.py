# -*- coding: utf-8 -*-
"""ASAHIKAWA-Search-1 クローラー(テスト版)
旭川市公式サイトを最大30ページ収集し、docs/corpus/ にHTMLとして保存する。
"""
import os
import re
import time
import hashlib
import urllib.robotparser
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ===== 設定 =====
import sys

PROFILES = {
    "asahikawa": {
        "seeds": [
            "https://www.city.asahikawa.hokkaido.jp/",
            "https://www.atca.jp/",
        ],
        "domains": {"www.city.asahikawa.hokkaido.jp", "www.atca.jp"},
        "max_pages": 2000,
        "out_dir": "docs/corpus",
    },
    "fukagawa": {
        "seeds": [
            "https://www.city.fukagawa.lg.jp/kankou/index.html",
            "https://www.kitasorachi.com/",
        ],
        "domains": {"www.city.fukagawa.lg.jp", "www.kitasorachi.com"},
        "max_pages": 150,
        "out_dir": "docs/fukagawa/corpus",
        "path_rules": {"www.city.fukagawa.lg.jp": ["/kankou/"]},
    },
}

PROFILE = PROFILES[sys.argv[1] if len(sys.argv) > 1 else "asahikawa"]
SEED_URLS = PROFILE["seeds"]
ALLOWED_DOMAINS = PROFILE["domains"]
PATH_RULES = PROFILE.get("path_rules", {})

def path_ok(p):
    rules = PATH_RULES.get(p.netloc)
    if not rules:
        return True
    return any(p.path.startswith(r) for r in rules)
MAX_PAGES = PROFILE["max_pages"]          # テスト版の上限
DELAY_SEC = 1.0         # 1ページごとの待ち時間(サーバーへの配慮)
OUT_DIR = PROFILE["out_dir"]
USER_AGENT = "ASAHIKAWA-Search-1-Bot (student project)"

# ===== robots.txt の確認 =====
robots_cache = {}

def can_fetch(url):
    domain = urlparse(url).netloc
    if domain not in robots_cache:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"https://{domain}/robots.txt")
        try:
            rp.read()
        except Exception:
            rp = None
        robots_cache[domain] = rp
    rp = robots_cache[domain]
    if rp is None:
        return True
    return rp.can_fetch(USER_AGENT, url)

# ===== 本体 =====
def clean_text(soup):
    for tag in soup(["script", "style", "nav", "footer", "header", "form"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()

def crawl():
    os.makedirs(OUT_DIR, exist_ok=True)
    queue = list(SEED_URLS)
    seen = set(queue)
    saved = 0

    while queue and saved < MAX_PAGES:
        url = queue.pop(0)
        if not can_fetch(url):
            print(f"[skip robots] {url}")
            continue
        low = url.lower()
        if low.endswith((".pdf", ".jpg", ".jpeg", ".png", ".gif", ".zip",
                         ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
                         ".mp3", ".mp4", ".csv")):
            continue
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT},
                             timeout=(5, 10), stream=True)
            ctype = r.headers.get("Content-Type", "")
            if r.status_code != 200 or "text/html" not in ctype:
                r.close()
                continue
            raw = b""
            for chunk in r.iter_content(65536):
                raw += chunk
                if len(raw) > 2_000_000:
                    print(f"[skip large] {url}")
                    raw = None
                    break
            r.close()
        except Exception as e:
            print(f"[error] {url} : {e}")
            continue
        if raw is None:
            continue
        # 文字コードを中身から自動判定(文字化け対策)
        import chardet
        guess = chardet.detect(raw[:20000])
        enc = guess.get("encoding") or "utf-8"
        try:
            page_text = raw.decode(enc, errors="replace")
        except LookupError:
            page_text = raw.decode("utf-8", errors="replace")
        soup = BeautifulSoup(page_text, "html.parser")

        title = soup.title.get_text(strip=True) if soup.title else url
        body_text = clean_text(soup)
        if len(body_text) < 100:
            continue  # 中身が薄いページは保存しない

        # 保存(ファイル名はURLのハッシュ)
        name = hashlib.md5(url.encode()).hexdigest() + ".html"
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as f:
            f.write(f"""<!DOCTYPE html>
<html lang="ja">
<head><meta charset="utf-8"><title>{title}</title>
<meta data-pagefind-meta="url[content]" content="{url}"></head>
<body>
<h1>{title}</h1>
<p><a href="{url}">{url}</a></p>
<main data-pagefind-body>{body_text}</main>
</body></html>""")
        saved += 1
        print(f"[{saved}/{MAX_PAGES}] {title[:40]} - {url}")

        # リンクを収集(同じドメインのみ)
        for a in soup.find_all("a", href=True):
            next_url = urljoin(url, a["href"]).split("#")[0]
            p = urlparse(next_url)
            if p.scheme in ("http", "https") and p.netloc in ALLOWED_DOMAINS and path_ok(p) and next_url not in seen:
                seen.add(next_url)
                queue.append(next_url)

        time.sleep(DELAY_SEC)

    print(f"\n完了: {saved} ページを {OUT_DIR} に保存しました")

if __name__ == "__main__":
    crawl()
