
"""
╔══════════════════════════════════════════════════════════════╗
║       🎬 CineGet v3 — Movie & Documentary Downloader         ║
║       Designed for Google Colab                              ║
║                                                              ║
║  ⚠️  LEGAL DISCLAIMER: Only download content you own or      ║
║     have legal rights to. Public-domain & Creative Commons   ║
║     films are freely downloadable. Respect copyright laws    ║
║     in your country.                                         ║
╚══════════════════════════════════════════════════════════════╝

HOW TO USE IN GOOGLE COLAB:
  1. Paste this entire script into a Colab cell and run it, OR
  2. Upload this file then run:  exec(open('movie_downloader_colab.py').read())

Sources (all tested to work from Colab's datacenter IPs):
  • YTS.mx          — mainstream movies (rich metadata + posters)
  • Knaben          — meta-search API (covers 1337x, TPB, RARBG archives, etc.)
  • Solidtorrents   — JSON API, strong on documentaries
  • BTDIG           — DHT crawler, finds obscure / niche content
  • ThePirateBay    — broad fallback via apibay.org
"""

# ─────────────────────────────────────────────────────────────
# STEP 1 — Install dependencies
# ─────────────────────────────────────────────────────────────
import subprocess, sys

def _run(cmd):
    subprocess.run(cmd, shell=True, check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

print("📦 Installing dependencies … (~30 s first time)")
_run("apt-get update -qq")
_run("apt-get install -y -qq aria2")
_run(f"{sys.executable} -m pip install -q requests beautifulsoup4 subliminal babelfish")
print("✅ Dependencies ready.\n")

# ─────────────────────────────────────────────────────────────
# STEP 2 — Imports
# ─────────────────────────────────────────────────────────────
import os, time, textwrap, urllib.parse, re, sys, json
import requests
from bs4 import BeautifulSoup
from IPython.display import display, HTML

# ── Colab-safe input ─────────────────────────────────────────
def ask(prompt: str) -> str:
    """Print prompt then read input — avoids Colab HTML-swallow bug."""
    print(prompt, end="", flush=True)
    sys.stdout.flush()
    return input()

# ─────────────────────────────────────────────────────────────
# STEP 3 — Configuration
# ─────────────────────────────────────────────────────────────
DOWNLOAD_ROOT = "/content/CineGet_Downloads"
QUALITY_ORDER = ["2160p", "1080p", "720p", "480p"]
TRACKERS = "&".join([
    "tr=udp://tracker.opentrackr.org:1337/announce",
    "tr=udp://open.tracker.cl:1337/announce",
    "tr=udp://tracker.openbittorrent.com:6969/announce",
    "tr=udp://tracker.internetwarriors.net:1337/announce",
    "tr=udp://exodus.desync.com:6969/announce",
    "tr=udp://tracker.cyberia.is:6969/announce",
    "tr=udp://tracker.torrent.eu.org:451/announce",
    "tr=udp://open.stealth.si:80/announce",
    "tr=udp://tracker.dler.org:6969/announce",
    "tr=udp://9.rarbg.to:2920/announce",
])
os.makedirs(DOWNLOAD_ROOT, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/json,*/*",
}

# ─────────────────────────────────────────────────────────────
# STEP 4 — Utility helpers
# ─────────────────────────────────────────────────────────────

def _get(url, params=None, timeout=15, json_body=None):
    try:
        if json_body is not None:
            r = requests.post(url, json=json_body, headers=HEADERS, timeout=timeout)
        else:
            r = requests.get(url, params=params, headers=HEADERS,
                             timeout=timeout, allow_redirects=True)
        r.raise_for_status()
        return r
    except Exception:
        return None

def _bytes(n):
    try:
        n = int(n)
    except Exception:
        return "?"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"

def _magnet(info_hash, name):
    return (
        f"magnet:?xt=urn:btih:{info_hash.strip()}"
        f"&dn={urllib.parse.quote(str(name))}"
        f"&{TRACKERS}"
    )

def _clean_query(raw: str) -> str:
    """
    Remove year in parens/brackets, extra punctuation, and lowercase.
    'Topuria Matador (2024)' → 'Topuria Matador'
    """
    q = re.sub(r"[\(\[\{]\s*\d{4}\s*[\)\]\}]", "", raw)  # strip (2024) / [2024]
    q = re.sub(r"[^\w\s\-\'\.]", " ", q)                  # remove other punct
    q = re.sub(r"\s{2,}", " ", q).strip()
    return q

def _entry(source, title, summary, magnet=None, seeders=0,
           detail_href=None, year="", rating="", genres=None, img=""):
    return {
        "_source":            source,
        "_magnet":            magnet,
        "_detail_href":       detail_href,
        "_seeders":           seeders,
        "title":              title,
        "year":               year,
        "rating":             rating,
        "genres":             genres or [],
        "medium_cover_image": img,
        "summary":            summary,
    }

# ─────────────────────────────────────────────────────────────
# STEP 5 — YTS (mainstream movies, rich metadata)
# ─────────────────────────────────────────────────────────────

def search_yts(query, limit=4):
    clean = _clean_query(query)
    r = _get("https://yts.mx/api/v2/list_movies.json",
             params={"query_term": clean, "limit": limit, "language": "en"})
    if not r:
        return []
    try:
        data = r.json()
        if data.get("status") == "ok" and data["data"]["movie_count"] > 0:
            for m in data["data"]["movies"]:
                m["_source"]   = "yts"
                m["_seeders"]  = 9999   # YTS always has seeds
                m["_magnet"]   = None
                m["_detail_href"] = None
            return data["data"]["movies"]
    except Exception:
        pass
    return []

# ─────────────────────────────────────────────────────────────
# STEP 6 — Knaben meta-search (covers 1337x, TPB, RARBG etc.)
# ─────────────────────────────────────────────────────────────
# Knaben is a JSON API that searches multiple sources internally.
# It is accessible from Colab datacenter IPs.

KNABEN_CATS = [
    "video",           # broad video bucket — catches most documentaries
]

def search_knaben(query, limit=8):
    clean = _clean_query(query)
    results = []
    for cat in KNABEN_CATS:
        body = {
            "search_term":    clean,
            "search_type":    "title",
            "categories":     [cat],
            "limit":          limit,
            "orderBy":        "seeders",
            "orderDirection": "desc",
        }
        r = _get("https://api.knaben.eu/v1", json_body=body)
        if not r:
            continue
        try:
            data = r.json()
            for item in data.get("hits", [])[:limit]:
                ih    = item.get("hash", "")
                title = item.get("title", "")
                if not ih or not title:
                    continue
                results.append(_entry(
                    source  = "knaben",
                    title   = title,
                    summary = (
                        f"🌱 Seeders: {item.get('seeders','?')}  |  "
                        f"💾 Size: {_bytes(item.get('bytes', 0))}"
                    ),
                    magnet  = _magnet(ih, title),
                    seeders = int(item.get("seeders", 0)),
                ))
        except Exception:
            continue
        if results:
            break
    return results

# ─────────────────────────────────────────────────────────────
# STEP 7 — Solidtorrents JSON API (strong on documentaries)
# ─────────────────────────────────────────────────────────────

def search_solidtorrents(query, limit=6):
    clean = _clean_query(query)
    # Try both the .to and .net domains
    for base in ("https://solidtorrents.to", "https://solidtorrents.eu"):
        r = _get(f"{base}/api/v1/search",
                 params={"q": clean, "category": "Video", "sort": "seeders"})
        if not r:
            continue
        try:
            data = r.json()
            items = data.get("results", [])
            results = []
            for item in items[:limit]:
                swarm = item.get("swarm", {})
                title = item.get("title", "")
                mag   = item.get("magnet", "")
                if not title or not mag:
                    continue
                # Re-append our trackers
                mag_base = mag.split("&tr=")[0]
                results.append(_entry(
                    source  = "solid",
                    title   = title,
                    summary = (
                        f"🌱 Seeders: {swarm.get('seeders','?')}  |  "
                        f"💾 Size: {_bytes(item.get('size', 0))}"
                    ),
                    magnet  = f"{mag_base}&{TRACKERS}",
                    seeders = int(swarm.get("seeders", 0)),
                ))
            if results:
                return results
        except Exception:
            continue
    return []

# ─────────────────────────────────────────────────────────────
# STEP 8 — BTDIG DHT search (finds niche / obscure content)
# ─────────────────────────────────────────────────────────────

def search_btdig(query, limit=5):
    """
    Scrape BTDIG.com — a DHT (Distributed Hash Table) index.
    Great for niche documentaries that aren't on mainstream trackers.
    """
    clean = _clean_query(query)
    r = _get("https://btdig.com/search",
             params={"q": clean, "order": 0})   # order 0 = relevance
    if not r:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for item in soup.select(".one_result")[:limit]:
        try:
            name_el = item.select_one(".torrent_name a")
            if not name_el:
                continue
            title = name_el.get_text(strip=True)

            mag_el = item.select_one('a[href^="magnet:"]')
            if not mag_el:
                continue
            mag_base = mag_el["href"].split("&tr=")[0]

            size_el = item.select_one(".torrent_size")
            size_str = size_el.get_text(strip=True) if size_el else "?"

            results.append(_entry(
                source  = "btdig",
                title   = title,
                summary = f"💾 Size: {size_str}  (DHT index — seeds unknown)",
                magnet  = f"{mag_base}&{TRACKERS}",
                seeders = 0,
            ))
        except Exception:
            continue
    return results

# ─────────────────────────────────────────────────────────────
# STEP 9 — ThePirateBay (broad fallback)
# ─────────────────────────────────────────────────────────────

def search_tpb(query, limit=5):
    clean = _clean_query(query)
    for cat in ("200", "0"):
        for ep in ("https://apibay.org/q.php", "https://pirates-bay.net/q.php"):
            r = _get(ep, params={"q": clean, "cat": cat})
            if not r:
                continue
            raw = r.text.strip()
            if raw in ("", "[]"):
                continue
            try:
                items = r.json()
                if not isinstance(items, list) or not items:
                    continue
                if items[0].get("id") == "0":
                    continue
                results = []
                for item in items[:limit]:
                    title = item.get("name", "Unknown")
                    results.append(_entry(
                        source  = "tpb",
                        title   = title,
                        summary = (
                            f"🌱 Seeders: {item.get('seeders','?')}  |  "
                            f"👥 Leechers: {item.get('leechers','?')}  |  "
                            f"💾 Size: {_bytes(item.get('size', 0))}"
                        ),
                        magnet  = _magnet(item["info_hash"], title),
                        seeders = int(item.get("seeders", 0)),
                    ))
                if results:
                    return results
            except Exception:
                continue
    return []

# ─────────────────────────────────────────────────────────────
# STEP 10 — 1337x (attempt — may be blocked on some Colab IPs)
# ─────────────────────────────────────────────────────────────

X_MIRRORS = [
    "https://1337x.to",
    "https://1337x.st",
    "https://x1337x.ws",
    "https://1337x.gd",
]

def _x_get(path):
    for base in X_MIRRORS:
        r = _get(f"{base}{path}", timeout=10)
        if r and len(r.text) > 500:
            return r
    return None

def search_1337x(query, limit=5):
    clean = _clean_query(query)
    enc   = urllib.parse.quote(clean)
    paths = [
        f"/category-search/{enc}/Documentaries/1/",
        f"/search/{enc}/1/",
    ]
    seen, results = set(), []
    for path in paths:
        if len(results) >= limit:
            break
        r = _x_get(path)
        if not r:
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for row in soup.select("table.table-list tbody tr"):
            if len(results) >= limit:
                break
            try:
                links = row.select("td.name a")
                if len(links) < 2:
                    continue
                href  = links[1].get("href", "")
                title = links[1].get_text(strip=True)
                if not href or title.lower() in seen:
                    continue
                seen.add(title.lower())

                seeds_td  = row.select_one("td.seeds")
                leeches_td= row.select_one("td.leeches")
                size_td   = row.select_one("td.size")

                seeds_n  = int(re.sub(r"[^\d]", "", seeds_td.text   or "0") or 0) if seeds_td   else 0
                leech_n  = int(re.sub(r"[^\d]", "", leeches_td.text or "0") or 0) if leeches_td else 0
                size_str = " ".join(re.sub(r"\s+", " ", size_td.text.strip()).split()[:2]) if size_td else "?"

                results.append(_entry(
                    source       = "1337x",
                    title        = title,
                    summary      = f"🌱 Seeders: {seeds_n}  |  👥 Leechers: {leech_n}  |  💾 Size: {size_str}",
                    detail_href  = href,
                    seeders      = seeds_n,
                    genres       = ["Documentary"],
                ))
            except Exception:
                continue
    return results

def fetch_1337x_magnet(detail_href):
    r = _x_get(detail_href)
    if not r:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if href.startswith("magnet:"):
            return href.split("&tr=")[0] + "&" + TRACKERS
    return None

# ─────────────────────────────────────────────────────────────
# STEP 11 — YTS torrent selection
# ─────────────────────────────────────────────────────────────

def best_yts_torrent(movie):
    torrents = movie.get("torrents", [])
    if not torrents:
        return None
    by_q = {t["quality"]: t for t in torrents}
    for q in QUALITY_ORDER:
        if q in by_q:
            return by_q[q]
    return torrents[0]

def yts_magnet(movie, torrent):
    return _magnet(torrent["hash"], movie["title"])

# ─────────────────────────────────────────────────────────────
# STEP 12 — Display helpers
# ─────────────────────────────────────────────────────────────

CARD_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@300;400;600&display=swap');
  .cg-wrap   { max-width:740px; font-family:'Inter',sans-serif; }
  .cg-card   {
    display:flex; gap:20px; padding:18px 22px;
    background:linear-gradient(135deg,#0d0d1a 0%,#1a1a2e 100%);
    border-radius:14px; color:#eee;
    border:1px solid #2a2a4a; box-shadow:0 8px 32px rgba(0,0,0,.5);
  }
  .cg-poster { height:220px; border-radius:8px; object-fit:cover;
               box-shadow:0 4px 20px rgba(0,0,0,.7); flex-shrink:0; }
  .cg-no-poster {
    height:220px; width:148px; border-radius:8px; background:#111;
    display:flex; align-items:center; justify-content:center;
    font-size:44px; flex-shrink:0; border:1px solid #2a2a4a;
  }
  .cg-meta   { display:flex; flex-direction:column; gap:8px; flex:1; }
  .cg-title  { font-family:'Bebas Neue',sans-serif; font-size:2rem;
               color:#e94560; line-height:1.1; margin:0; }
  .cg-year   { color:#777; font-size:.85rem; margin-left:6px; }
  .cg-badge  { display:inline-block; background:#e94560; color:#fff;
               padding:2px 9px; border-radius:20px; font-size:.72rem;
               font-weight:700; margin:2px; }
  .cg-badge.genre { background:transparent; border:1px solid #e94560; color:#e94560; }
  .cg-badge.src   { background:#2a2a4a; color:#aaa; font-weight:400; }
  .cg-summary { font-size:.82rem; color:#aaa; line-height:1.55; }
  .cg-row    { display:flex; flex-wrap:wrap; gap:4px; align-items:center; }
  .cg-banner {
    font-family:monospace; padding:9px 16px;
    background:#16213e; color:#e94560; border-radius:8px;
    border-left:4px solid #e94560; font-size:.9rem; max-width:740px;
  }
</style>
"""

SRC_LABEL = {
    "yts":    "YTS",
    "knaben": "Knaben",
    "solid":  "Solidtorrents",
    "btdig":  "BTDIG",
    "tpb":    "TPB",
    "1337x":  "1337x",
}

def display_card(movie):
    title   = movie.get("title", "Unknown")
    year    = movie.get("year", "")
    rating  = movie.get("rating", "")
    genres  = movie.get("genres", [])
    summary = movie.get("summary", "")
    img_url = movie.get("medium_cover_image", "")
    src     = movie.get("_source", "yts")

    rating_badge = f'<span class="cg-badge">⭐ {rating}</span>' if rating else ""
    genre_badges = "".join(
        f'<span class="cg-badge genre">{g}</span>' for g in (genres or [])[:4])
    src_badge = f'<span class="cg-badge src">via {SRC_LABEL.get(src, src)}</span>'

    poster = (
        f'<img class="cg-poster" src="{img_url}" '
        f'onerror="this.style.display=\'none\';'
        f'this.nextElementSibling.style.display=\'flex\'">'
        f'<div class="cg-no-poster" style="display:none">🎬</div>'
        if img_url else '<div class="cg-no-poster">🎬</div>'
    )
    summary_short = textwrap.shorten(summary, width=340, placeholder="…")

    display(HTML(f"""
    {CARD_CSS}
    <div class="cg-wrap"><div class="cg-card">
      {poster}
      <div class="cg-meta">
        <p class="cg-title">{title}<span class="cg-year">{year}</span></p>
        <div class="cg-row">{rating_badge}{genre_badges}{src_badge}</div>
        <p class="cg-summary">{summary_short}</p>
      </div>
    </div></div>
    """))

def show_list(results):
    for i, m in enumerate(results, 1):
        year  = f" ({m['year']})" if m.get("year") else ""
        src   = f" [{SRC_LABEL.get(m.get('_source',''),'?')}]"
        seeds = f"  🌱{m['_seeders']}" if m.get("_seeders") else ""
        print(f"  [{i}] {m['title']}{year}{src}{seeds}")
    print()

def banner(msg):
    display(HTML(f'{CARD_CSS}<div class="cg-banner">{msg}</div>'))

# ─────────────────────────────────────────────────────────────
# STEP 13 — English subtitle downloader
# ─────────────────────────────────────────────────────────────

def download_subtitles(video_path):
    try:
        import subliminal, babelfish
        video = subliminal.scan_video(video_path)
        subs  = subliminal.download_best_subtitles(
            [video], {babelfish.Language("eng")}, only_one=True)
        if subs:
            subliminal.save_subtitles(video, subs[video])
            print("  ✅ English subtitle saved.")
        else:
            print("  ℹ️  No subtitle found via Subliminal.")
    except Exception as e:
        print(f"  ⚠️  Subtitle skipped: {e}")

# ─────────────────────────────────────────────────────────────
# STEP 14 — aria2c downloader
# ─────────────────────────────────────────────────────────────

def _safe_name(name):
    return "".join(c for c in name if c.isalnum() or c in " -_()").strip() or "download"

def download_magnet(magnet, title):
    out_dir = os.path.join(DOWNLOAD_ROOT, _safe_name(title))
    os.makedirs(out_dir, exist_ok=True)
    cmd = (
        f'aria2c '
        f'--dir="{out_dir}" '
        f'--seed-time=0 '
        f'--max-connection-per-server=8 '
        f'--split=8 '
        f'--bt-max-peers=80 '
        f'--bt-enable-lpd=true '
        f'--file-allocation=none '
        f'--console-log-level=warn '
        f'--summary-interval=15 '
        f'"{magnet}"'
    )
    print(f"\n🚀 Downloading to: {out_dir}")
    print("─" * 60)
    print("⏳ aria2c running … press  Interrupt Kernel  to stop.\n")
    os.system(cmd)
    return out_dir

# ─────────────────────────────────────────────────────────────
# STEP 15 — Main interactive flow
# ─────────────────────────────────────────────────────────────

def run():
    display(HTML(f"""
    {CARD_CSS}
    <div class="cg-wrap">
      <div style="font-family:'Bebas Neue',sans-serif;font-size:2.6rem;
                  color:#e94560;letter-spacing:3px;line-height:1.1;">🎬 CineGet v3</div>
      <div style="color:#555;font-size:.82rem;margin-top:2px;">
        Movies &amp; Documentaries &nbsp;·&nbsp;
        YTS &nbsp;·&nbsp; Knaben &nbsp;·&nbsp; Solidtorrents &nbsp;·&nbsp;
        BTDIG &nbsp;·&nbsp; TPB &nbsp;·&nbsp; 1337x
      </div>
    </div>
    """))

    # ── 15.1  Query ──────────────────────────────────────────
    time.sleep(0.15)
    raw_query = ask("\n🎬 Enter movie / documentary name: ").strip()
    if not raw_query:
        print("No input — exiting.")
        return

    clean = _clean_query(raw_query)
    print(f'\n🔍 Searching for: "{clean}"  (cleaned from: "{raw_query}")\n')

    # ── 15.2  Search all sources ─────────────────────────────
    def _search(label, fn, *args):
        print(f"   ├─ {label:<18}", end=" ", flush=True)
        try:
            res = fn(*args)
            print(f"✓ {len(res)} found" if res else "✗ none")
            return res
        except Exception as e:
            print(f"✗ error: {e}")
            return []

    yts    = _search("YTS …",            search_yts,           raw_query, 4)
    knaben = _search("Knaben …",         search_knaben,        raw_query, 8)
    solid  = _search("Solidtorrents …",  search_solidtorrents, raw_query, 6)
    btdig  = _search("BTDIG …",          search_btdig,         raw_query, 5)
    tpb    = _search("ThePirateBay …",   search_tpb,           raw_query, 5)
    x37    = _search("1337x …",          search_1337x,         raw_query, 4)
    print(f"   └─ {'─'*28}")

    # ── 15.3  Merge + deduplicate ────────────────────────────
    combined, seen = [], set()

    # YTS first (best quality / metadata)
    for r in yts:
        key = re.sub(r"\W", "", r["title"].lower())[:40]
        if key not in seen:
            seen.add(key); combined.append(r)

    # Rest sorted by seeders descending
    rest = knaben + solid + btdig + tpb + x37
    rest.sort(key=lambda r: r.get("_seeders", 0), reverse=True)
    for r in rest:
        key = re.sub(r"\W", "", r["title"].lower())[:40]
        if key not in seen:
            seen.add(key); combined.append(r)

    combined = combined[:12]

    if not combined:
        print("\n❌ Nothing found across all sources.")
        print("   Tips: use shorter title, try without year, check spelling.")
        return

    # ── 15.4  Show list ──────────────────────────────────────
    print(f"\n✅ {len(combined)} result(s) found:\n")
    show_list(combined)

    # ── 15.5  User picks ─────────────────────────────────────
    try:
        pick = int(ask(f"👉 Select [1–{len(combined)}]  or  0 to cancel: "))
    except ValueError:
        print("Invalid — exiting."); return

    if pick == 0:
        print("Cancelled."); return
    if not (1 <= pick <= len(combined)):
        print("Out of range — exiting."); return

    movie = combined[pick - 1]

    # ── 15.6  Detail card ────────────────────────────────────
    print()
    display_card(movie)
    print()

    # ── 15.7  Resolve magnet ─────────────────────────────────
    src = movie.get("_source", "yts")

    if src == "yts":
        torrent = best_yts_torrent(movie)
        if not torrent:
            print("❌ No torrent found for this YTS entry."); return
        magnet   = yts_magnet(movie, torrent)
        size_str = torrent.get("size", "?")
        qual_str = torrent.get("quality", "?")

    elif src == "1337x":
        print("🔗 Fetching magnet from 1337x …", end=" ", flush=True)
        magnet = fetch_1337x_magnet(movie["_detail_href"])
        if not magnet:
            print("\n❌ Could not get magnet. Try another result."); return
        print("✓")
        size_str = movie["summary"].split("Size:")[-1].strip() if "Size:" in movie["summary"] else "?"
        qual_str = "original"

    else:
        # knaben / solid / btdig / tpb — magnet already in dict
        magnet = movie.get("_magnet", "")
        if not magnet:
            print("❌ No magnet link available for this result."); return
        size_str = movie["summary"].split("Size:")[-1].strip() if "Size:" in movie["summary"] else "?"
        qual_str = "original"

    banner(
        f"📦 Quality: <b>{qual_str}</b> &nbsp;|&nbsp; "
        f"Size: <b>{size_str}</b> &nbsp;|&nbsp; "
        f"Source: <b>{SRC_LABEL.get(src, src)}</b>"
    )
    print()

    # ── 15.8  Confirm ────────────────────────────────────────
    time.sleep(0.1)
    answer = ask("⬇️  Download this? (yes / no): ").strip().lower()
    if answer not in ("yes", "y"):
        print("Download cancelled."); return

    # ── 15.9  Download ───────────────────────────────────────
    out_dir = download_magnet(magnet, movie["title"])

    # ── 15.10  Subtitles ─────────────────────────────────────
    print("\n🔤 Looking for English subtitles …")
    video_file = None
    for root, _, files in os.walk(out_dir):
        for f in files:
            if f.lower().endswith((".mp4", ".mkv", ".avi", ".mov")):
                candidate = os.path.join(root, f)
                if video_file is None or os.path.getsize(candidate) > os.path.getsize(video_file):
                    video_file = candidate
    if video_file:
        download_subtitles(video_file)
    else:
        print("  ℹ️  Video not yet on disk — subtitle fetch skipped.")

    # ── 15.11  Done ──────────────────────────────────────────
    print()
    banner(f"🎉 Done!  Saved to: <code>{out_dir}</code>")
    print()
    print("📂 Contents:")
    os.system(f'ls -lh "{out_dir}"')
    print()
    print("💡 To keep files permanently, mount Google Drive first:")
    print("   from google.colab import drive; drive.mount('/content/drive')")
    print(f"   Then:  !cp -r '{out_dir}' /content/drive/MyDrive/")


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    run()
