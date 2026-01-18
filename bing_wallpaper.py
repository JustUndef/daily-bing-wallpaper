# -*- coding: utf-8 -*-
import argparse
import ctypes
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
import urllib.parse

import requests

# Import logging
from logger import setup_logger

BING_BASE = "https://www.bing.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Config file location
CONFIG_FILE = Path(os.getenv('APPDATA', '')) / 'BingWallpaperDownloader' / 'config.json'

# Initialize logger
logger = setup_logger('downloader')

def load_config() -> dict:
    """Load configuration from JSON file"""
    import time
    
    if not CONFIG_FILE.exists():
        # Wait for installer to write config - poll for up to 3 seconds
        # This handles race condition where installer is writing config as app starts
        logger.info("Config file not found, waiting for installer to write it...")
        max_wait_time = 3.0  # Maximum 3 seconds to wait
        poll_interval = 0.1  # Check every 100ms
        waited = 0.0
        
        while waited < max_wait_time:
            time.sleep(poll_interval)
            waited += poll_interval
            
            if CONFIG_FILE.exists():
                logger.info(f"Config file appeared after {waited:.1f}s - installer created it")
                break
        
        # If still doesn't exist after waiting, create default config
        if not CONFIG_FILE.exists():
            logger.info("Config file still not found after waiting - creating default config")
            default_config = {
                "download_folder": str(Path.home() / "Pictures" / "BingWallpapers"),
                "market": "de-DE",
                "fallback_markets": "en-US",
                "resolution": "UHD,3840x2160,2560x1440,1920x1200,1920x1080",
                "image_count": 8,
                "set_latest": False,
                "file_mode": "skip",
                "name_mode": "slug"
            }
            try:
                CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2)
                logger.info(f"Created default config file: {CONFIG_FILE}")
            except Exception as e:
                logger.warning(f"Could not create config file: {e}")
            return default_config
    
    # Config file exists - load it
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            logger.info(f"Loaded config from {CONFIG_FILE}")
            return config
    except Exception as e:
        logger.warning(f"Could not load config file: {e}")
        return {}

def fetch_image_json(mkt: str, idx: int) -> Optional[dict]:
    url = (
        f"{BING_BASE}/HPImageArchive.aspx?"
        f"format=js&idx={idx}&n=1&mkt={urllib.parse.quote(mkt)}"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        imgs = data.get("images") or []
        result = imgs[0] if imgs else None
        if result:
            logger.info(f"Fetched image metadata for market={mkt}, idx={idx}")
        else:
            logger.warning(f"No images found for market={mkt}, idx={idx}")
        return result
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch image metadata: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching metadata: {e}", exc_info=True)
        return None

def build_candidate_urls(img: dict, preferred_res: List[str]) -> List[str]:
    urls = []
    url = img.get("url")
    urlbase = img.get("urlbase")
    if url:
        urls.append(urllib.parse.urljoin(BING_BASE, url))
    if urlbase:
        base = urllib.parse.urljoin(BING_BASE, urlbase)
        for res in preferred_res:
            for ext in [".jpg", ".png", ".webp"]:
                urls.append(f"{base}_{res}{ext}")
    # Dedupe keep order
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out

def guess_ext_from_ct(ct: Optional[str]) -> str:
    if not ct:
        return ".jpg"
    ct = ct.lower()
    if "jpeg" in ct or "jpg" in ct: return ".jpg"
    if "png" in ct: return ".png"
    if "webp" in ct: return ".webp"
    if "bmp" in ct: return ".bmp"
    return ".jpg"

def download_first(urls: List[str]) -> Tuple[bytes, str]:
    last = None
    with requests.Session() as s:
        for u in urls:
            try:
                r = s.get(u, headers=HEADERS, timeout=30)
                r.raise_for_status()
                data = r.content
                if len(data) < 10 * 1024:
                    last = RuntimeError("Response too small")
                    logger.warning(f"Image too small from {u[:50]}...")
                    continue
                ct = r.headers.get("Content-Type", "") or "image/jpeg"
                logger.info(f"Successfully downloaded image ({len(data)} bytes)")
                return data, ct
            except Exception as e:
                logger.warning(f"Failed to download from {u[:50]}...: {e}")
                last = e
    logger.error("All download attempts failed")
    raise last or RuntimeError("Download failed")

def sanitize(name: str) -> str:
    for ch in '<>:"/\\|?*':
        name = name.replace(ch, "_")
    return name.strip()

def extract_slug(img: dict) -> str:
    # urlbase z. B. /th?id=OHR.Waterfall_DE-de12345
    ub = img.get("urlbase") or ""
    # nimm Teil nach 'OHR.' bis zum nächsten '_' oder Ende
    if "OHR." in ub:
        slug = ub.split("OHR.", 1)[1]
    else:
        slug = ub.rsplit("/", 1)[-1]
    # bis zum ersten '_' trennen
    slug = slug.split("_", 1)[0]
    return slug or "unknown"

def date_from_img(img: dict) -> str:
    raw = img.get("startdate")  # yyyyMMdd
    try:
        return datetime.strptime(raw, "%Y%m%d").strftime("%Y-%m-%d")
    except Exception:
        return raw or datetime.utcnow().strftime("%Y-%m-%d")

def build_filename(img: dict, ct: str, name_mode: str = "slug") -> str:
    d = date_from_img(img)
    slug = extract_slug(img)
    title = img.get("title") or ""
    if name_mode == "title" and title:
        base = f"{d}_{title}"
    else:
        base = f"{d}_{slug}"
    base = sanitize(base)
    if len(base) > 140:
        base = base[:140].rstrip("_")
    return base + guess_ext_from_ct(ct)

def set_wallpaper(path: Path):
    SPI_SETDESKWALLPAPER = 20
    SPIF_UPDATEINIFILE = 0x01
    SPIF_SENDWININICHANGE = 0x02
    ok = ctypes.windll.user32.SystemParametersInfoW(
        SPI_SETDESKWALLPAPER, 0, str(path.resolve()), SPIF_UPDATEINIFILE | SPIF_SENDWININICHANGE
    )
    if ok == 0:
        raise ctypes.WinError()

def pick_and_download(markets: List[str], idx: int, preferred_res: List[str]) -> Optional[Tuple[bytes, str, dict]]:
    last = None
    for mkt in markets:
        try:
            img = fetch_image_json(mkt, idx)
            if not img:
                continue
            urls = build_candidate_urls(img, preferred_res)
            data, ct = download_first(urls)
            return data, ct, img
        except Exception as e:
            last = e
            continue
    if last:
        print(f"Warnung idx={idx}: {last}", file=sys.stderr)
    return None

def main():
    logger.info("=== Bing Wallpaper Downloader Starting ===")
    import argparse
    
    # Load config file first
    config = load_config()
    logger.info(f"Config loaded from: {CONFIG_FILE}")
    
    # Set defaults from config file, can be overridden by CLI args
    p = argparse.ArgumentParser("Bing week downloader (HPImageArchive) with robust dedupe")
    p.add_argument("--mkt", default=config.get("market", "de-DE"))
    p.add_argument("--fallback-mkts", default=config.get("fallback_markets", "en-US"))
    p.add_argument("--count", type=int, default=config.get("image_count", 8))
    p.add_argument("--out", default=config.get("download_folder", str(Path.home() / "Pictures" / "BingWallpapers")))
    p.add_argument("--res", default=config.get("resolution", "UHD,3840x2160,2560x1440,1920x1200,1920x1080"))
    p.add_argument("--mode", choices=["skip","unique","overwrite"], default=config.get("file_mode", "skip"),
                   help="skip: existierende Zieldatei nicht neu schreiben; "
                        "unique: falls gleicher Name existiert, _1, _2 anhängen; "
                        "overwrite: bestehende Datei gleichen Namens überschreiben.")
    p.add_argument("--name-mode", choices=["slug","title"], default=config.get("name_mode", "slug"),
                   help="Dateiname aus OHR-Slug (robust) oder aus Titel.")
    p.add_argument("--set-latest", action="store_true", default=config.get("set_latest", False))
    args = p.parse_args()

    out_dir = Path(args.out); out_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Download directory: {out_dir}")
    preferred_res = [x.strip() for x in args.res.split(",") if x.strip()]
    markets = [args.mkt.strip()] + [m.strip() for m in args.fallback_mkts.split(",") if m.strip()]
    logger.info(f"Markets: {markets}, Resolutions: {preferred_res}")

    user_paused = config.get("user_paused", False)

    saved: List[Path] = []
    latest_path: Optional[Path] = None

    # Für unique-Mode Suffixzählung
    def next_unique_path(base: Path) -> Path:
        if not base.exists():
            return base
        i = 1
        while True:
            cand = base.with_stem(f"{base.stem}_{i}")
            if not cand.exists():
                return cand
            i += 1

    for idx in range(0, min(8, max(1, args.count))):
        logger.info(f"Fetching image idx={idx}")
        res = pick_and_download(markets, idx, preferred_res)
        if not res:
            logger.warning(f"Failed to download image idx={idx}")
            continue
        data, ct, img = res
        fname = build_filename(img, ct, name_mode=args.name_mode)
        target = out_dir / fname

        if args.mode == "skip" and target.exists():
            # kein Speichern, kein _1
            logger.info(f"Skipping existing file: {fname}")
            saved.append(target)
            if idx == 0:
                latest_path = target
            continue
        elif args.mode == "overwrite":
            target.write_bytes(data)
            logger.info(f"Overwrote: {fname}")
        else:  # unique
            target = next_unique_path(target)
            target.write_bytes(data)
            logger.info(f"Saved: {target.name}")

        saved.append(target)
        if idx == 0:
            latest_path = target

    if not saved:
        logger.info("No new images downloaded (all already exist)")
        print("Nichts heruntergeladen oder alles vorhanden.")
        return 0

    logger.info(f"Downloaded {len(saved)} images")
    print("Gespeichert:")
    for pth in saved:
        print(f"- {pth.name}")

    if args.set_latest and not user_paused and latest_path:
        try:
            set_wallpaper(latest_path)
            logger.info(f"Wallpaper set to: {latest_path.name}")
            print(f"Wallpaper gesetzt: {latest_path}")
        except Exception as e:
            logger.error(f"Failed to set wallpaper: {e}", exc_info=True)
            print(f"Wallpaper setzen fehlgeschlagen: {e}", file=sys.stderr)
            return 1
    
    logger.info("=== Bing Wallpaper Downloader Completed Successfully ===")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Fehler: {e}", file=sys.stderr)
        sys.exit(1)