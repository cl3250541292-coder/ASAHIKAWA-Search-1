# -*- coding: utf-8 -*-
# 使い方: Codespaceのリポジトリ直下で  python build_curated.py
# 生成物: docs/curated.json (キーワード→動画リスト。動画タブ/すべてタブで使用)
import json, re, time, urllib.request, urllib.parse, datetime

UA = {"User-Agent": "Mozilla/5.0 (curated-builder)"}

# ---- 手動で指定した個別動画: キーワード -> {pin:[最優先ID], vids:[通常ID...]} ----
MANUAL = {
  "ゴールデンカムイ": {"pin": ["H4cw3kEE0ZQ"],
      "vids": ["8b3MdkhyHHw","t31CLh9hUZY","vt7o58bX-6M","SF8jW6paGZ0","ffEdXd545tw","2loIAVv7GYQ","eMfHq5nTGsw"]},
  "カムイの歌": {"pin": ["wlUiDIEz0r8"],
      "vids": ["6Cuekd1bzdI","br0JPp6mqSU","U6D11Sk-gXg","5MrfBjcBdwY","uEAn5Gdxziw","aORWqSzTy4U"]},
  "東川": {"pin": ["wlUiDIEz0r8"],
      "vids": ["6Cuekd1bzdI","br0JPp6mqSU","U6D11Sk-gXg","5MrfBjcBdwY","uEAn5Gdxziw","aORWqSzTy4U"]},
  "ムックリ": {"pin": [], "vids": ["YsLHLRar7Pw","UN_D24T3fJ4","wGdW6AqKVw0"]},
  "サイパル": {"pin": [], "vids": ["es-wu56CUjI","bH2lq1798xs","oSrN1OnTsqM","qUs-8U4Mz0Q","umAwBQMmPS4"]},
  "旭山動物園": {"pin": [], "vids": ["7pXujl3I1hs","-MbLIUu0c5w","t4kzvVCDgTY"]},
  "旭川駅": {"pin": [], "vids": ["TvRzKnH341U"]},
  "旭川市": {"pin": [], "vids": ["ZSuGEyh1h-U"]},
  "男山": {"pin": [], "vids": ["cVi044dICXM","_-5dAIZdVoc","ITxsIChOBa4","iETX2ApDGkU","IfJ-000yZ48"]},
  "あさひかわラーメン": {"pin": [], "vids": ["eBvfP3OAgSI","PXiqBgH0Xbs"]},
  "上野ファーム": {"pin": [], "vids": ["3LmU2mnb6D8","Cy7Dxl8bGF0"]},
  "旭川空港": {"pin": [], "vids": ["I99FmwaRVQ4","cwDIHPuiSo4","Uos-dWhoMyI"]},
  "き花": {"pin": [], "vids": ["j-YJQvU1SJU","ezXuJoSHFqY","ehxwtiKGjdk"]},
  "カステラ": {"pin": [], "vids": ["CABJK4bo-jg"]},
  "旭川家具": {"pin": [], "vids": ["ragdOHw1zp0"]},
  "深川農道音楽祭": {"pin": [], "vids": ["MUNZCQB8nlI","OAvkXcSbLsk","aCX2VioVOKY","ck2WtoWnqug"]},
}

# ---- チャンネル自動取得: キーワード -> handle または channel_id, n=取得本数 ----
CHANNELS = {
  "まちなかキャンパス": {"handle": "@asahikawamachinakacampus9744", "n": 6},
  "DESIGN":           {"handle": "@design_asahikawa", "n": 6},
  "き花":             {"handle": "@tsuboyasohonten", "n": 4},
  "旭川家具":         {"handle": "@asahikawadesigncenter6083", "n": 6},
  "深川農道音楽祭":   {"handle": "@nouon_fukagawa", "n": 6},
  "安全地帯":         {"handle": "@anzenchitaisaltmoderate5328", "n": 6},
  "東川":             {"channel_id": "UCrt9whvvry_2-zMjF4NznvA", "n": 6},
}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")

def oembed(vid):
    """動画ID -> (title, channel)。失敗時は(None,None)"""
    try:
        u = "https://www.youtube.com/oembed?url=" + urllib.parse.quote(
            "https://www.youtube.com/watch?v=" + vid, safe="") + "&format=json"
        j = json.loads(get(u))
        return j.get("title"), j.get("author_name")
    except Exception as e:
        print("  oembed失敗", vid, e)
        return None, None

def resolve_handle(handle):
    """@handle -> channel_id(UC...)"""
    try:
        html = get("https://www.youtube.com/" + handle)
        m = re.search(r'"channelId":"(UC[\w-]{22})"', html) or \
            re.search(r'channel/(UC[\w-]{22})', html)
        return m.group(1) if m else None
    except Exception as e:
        print("  handle解決失敗", handle, e)
        return None

def fetch_rss(channel_id, n):
    """channel_id -> [{id,title,channel,date}] 最新n件"""
    out = []
    try:
        xml = get("https://www.youtube.com/feeds/videos.xml?channel_id=" + channel_id)
        author = (re.search(r"<author>\s*<name>(.*?)</name>", xml, re.S) or [None, ""])[1].strip()
        for ent in re.findall(r"<entry>(.*?)</entry>", xml, re.S)[:n]:
            vid = (re.search(r"<yt:videoId>(.*?)</yt:videoId>", ent) or [None, ""])[1]
            title = (re.search(r"<title>(.*?)</title>", ent) or [None, ""])[1]
            date = (re.search(r"<published>(.*?)</published>", ent) or [None, ""])[1]
            if vid:
                out.append({"id": vid, "title": title, "channel": author, "date": date})
    except Exception as e:
        print("  RSS失敗", channel_id, e)
    return out

def main():
    result = {}
    for kw, g in MANUAL.items():
        lst = []
        for vid in g["pin"]:
            t, c = oembed(vid); time.sleep(0.2)
            lst.append({"id": vid, "title": t or vid, "channel": c or "", "pin": True})
        for vid in g["vids"]:
            t, c = oembed(vid); time.sleep(0.2)
            lst.append({"id": vid, "title": t or vid, "channel": c or ""})
        result.setdefault(kw, []).extend(lst)
        print("手動", kw, len(lst), "本")
    for kw, ch in CHANNELS.items():
        cid = ch.get("channel_id") or resolve_handle(ch["handle"])
        if not cid:
            print("チャンネル解決できず", kw); continue
        vids = fetch_rss(cid, ch.get("n", 6))
        have = {v["id"] for v in result.get(kw, [])}
        add = [{"id": v["id"], "title": v["title"], "channel": v["channel"]} for v in vids if v["id"] not in have]
        result.setdefault(kw, []).extend(add)
        print("ch  ", kw, "->", cid, "追加", len(add), "本")

    out = {"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "keywords": result}
    with open("docs/curated.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    total = sum(len(v) for v in result.values())
    print("=== 完了: docs/curated.json / キーワード", len(result), "個 / 動画", total, "本 ===")

if __name__ == "__main__":
    main()
