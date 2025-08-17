# fetch_china_iptv.py (央视 + 卫视精简版)
# 从 iptv-org 拉取中国频道，只保留 CCTV & 卫视频道
# 用法：
#   python fetch_china_iptv.py --probe

import argparse
import re
import sys
import time
import requests

UA = "Mozilla/5.0 (compatible; ChinaIPTVFetcher/1.0)"
TIMEOUT = 7

# 直接取中国频道列表
IPTV_SOURCE = "https://iptv-org.github.io/iptv/countries/cn.m3u"

def fetch_text(url: str) -> str:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text

def parse_m3u(m3u_text: str):
    lines = [ln.strip() for ln in m3u_text.splitlines() if ln.strip()]
    items = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("#EXTINF"):
            extinf = ln
            name = ln.split(",", 1)[1].strip() if "," in ln else "Unknown"
            attrs = {}
            for m in re.finditer(r'(\w[\w-]*)="([^"]*)"', ln):
                attrs[m.group(1)] = m.group(2)
            url = ""
            if i + 1 < len(lines):
                nxt = lines[i + 1]
                if not nxt.startswith("#"):
                    url = nxt.strip()
                    i += 1
            if url:
                items.append({
                    "name": name,
                    "url": url,
                    "attrs": attrs,
                    "raw_extinf": extinf
                })
        i += 1
    return items

def filter_channels(items):
    """只保留 央视 和 卫视"""
    keep = []
    for it in items:
        name = it["name"]
        if name.startswith("CCTV"):   # 央视
            keep.append(it)
        elif "卫视" in name:         # 各省卫视
            keep.append(it)
    return keep

def dedupe_items(items):
    seen_url = set()
    result = []
    for it in items:
        if it["url"] in seen_url:
            continue
        seen_url.add(it["url"])
        result.append(it)
    return result

def write_m3u(path, items):
    with open(path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for it in items:
            f.write(it["raw_extinf"] + "\n")
            f.write(it["url"] + "\n")

def write_txt(path, items):
    with open(path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(f'{it["name"]}|{it["url"]}\n')

def probe_url(url: str) -> bool:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT, stream=True)
        return r.status_code in (200, 206)
    except Exception:
        return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true", help="探测可用性")
    args = ap.parse_args()

    sys.stderr.write("Fetching China IPTV list...\n")
    text = fetch_text(IPTV_SOURCE)
    all_items = parse_m3u(text)
    filtered = filter_channels(all_items)
    deduped = dedupe_items(filtered)

    sys.stderr.write(f"Total CCTV+卫视 channels: {len(deduped)}\n")

    write_m3u("china_tv_raw.m3u", deduped)
    write_txt("china_tv_raw.txt", deduped)

    if args.probe:
        alive = []
        for i, it in enumerate(deduped, 1):
            ok = probe_url(it["url"])
            sys.stderr.write(f"[{i}/{len(deduped)}] {'OK' if ok else 'BAD'} {it['name']}\n")
            if ok:
                alive.append(it)
            time.sleep(0.2)

        write_m3u("china_tv_alive.m3u", alive)
        write_txt("china_tv_alive.txt", alive)
        sys.stderr.write(f"Alive: {len(alive)}/{len(deduped)}\n")

if __name__ == "__main__":
    main()
