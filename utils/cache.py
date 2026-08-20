import os
import shutil
import json
from pathlib import Path
from typing import Optional, List

CACHE_DIR = Path(".cache/thumbnails")
PACKS_DIR = Path(".cache/packs")


def ensure_cache_dir() -> Path:
    """Ensure thumbnail cache directory exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    PACKS_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def get_cached_thumb_path(file_id: str) -> Optional[Path]:
    """Check if thumbnail file exists in local cache."""
    ensure_cache_dir()
    candidate_webp = CACHE_DIR / f"{file_id}.webp"
    if candidate_webp.exists() and candidate_webp.stat().st_size > 0:
        return candidate_webp

    candidate_png = CACHE_DIR / f"{file_id}.png"
    if candidate_png.exists() and candidate_png.stat().st_size > 0:
        return candidate_png

    candidate_raw = CACHE_DIR / file_id
    if candidate_raw.exists() and candidate_raw.stat().st_size > 0:
        return candidate_raw

    return None


def get_target_cache_path(file_id: str, file_path_on_server: str = "") -> Path:
    """Determine the destination path in cache for a file."""
    ensure_cache_dir()
    ext = os.path.splitext(file_path_on_server)[1] if file_path_on_server else ".webp"
    if not ext:
        ext = ".webp"
    return CACHE_DIR / f"{file_id}{ext}"


def clear_cache() -> None:
    """Clear all cached thumbnails."""
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR, ignore_errors=True)
    if PACKS_DIR.exists():
        shutil.rmtree(PACKS_DIR, ignore_errors=True)
    ensure_cache_dir()


from core.models import StickerPackData, StickerItem

def save_pack(pack: StickerPackData) -> None:
    ensure_cache_dir()
    pack_path = PACKS_DIR / f"{pack.name}.json"
    with open(pack_path, "w", encoding="utf-8") as f:
        json.dump(pack.to_dict(), f, ensure_ascii=False, indent=2)

def delete_pack_from_cache(pack_name: str, stickers: Optional[List[StickerItem]] = None) -> None:
    """Delete a pack's cached json and thumbnails from disk."""
    ensure_cache_dir()
    pack_path = PACKS_DIR / f"{pack_name}.json"
    if pack_path.exists():
        try:
            pack_path.unlink(missing_ok=True)
        except Exception:
            pass

    if stickers:
        for s in stickers:
            if s.local_thumb_path:
                try:
                    p = Path(s.local_thumb_path)
                    if p.exists() and CACHE_DIR.resolve() in p.resolve().parents:
                        p.unlink(missing_ok=True)
                except Exception:
                    pass
            elif s.thumb_file_id:
                thumb_path = get_cached_thumb_path(s.thumb_file_id)
                if thumb_path and thumb_path.exists():
                    try:
                        thumb_path.unlink(missing_ok=True)
                    except Exception:
                        pass

def load_all_packs() -> List[StickerPackData]:
    """Load all cached packs sorted chronologically by their download timestamp."""
    ensure_cache_dir()
    loaded_entries = []
    for file_path in PACKS_DIR.glob("*.json"):
        try:
            mtime = file_path.stat().st_mtime
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                pack = StickerPackData.from_dict(data)
                # Use stored timestamp or fallback to filesystem modification time
                ts = pack.downloaded_at if pack.downloaded_at is not None else mtime
                loaded_entries.append((ts, pack))
        except Exception:
            pass
    # Sort ascending so earlier downloads appear first and newer ones appear sequentially
    loaded_entries.sort(key=lambda x: x[0])
    return [entry[1] for entry in loaded_entries]


SELECTED_ORDER_FILE = Path(".cache/selected_order.json")

def save_selected_order(file_ids: List[str]) -> None:
    """Save the ordered list of selected sticker file_ids to disk."""
    ensure_cache_dir()
    try:
        with open(SELECTED_ORDER_FILE, "w", encoding="utf-8") as f:
            json.dump(file_ids, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def load_selected_order() -> List[str]:
    """Load the custom order of selected sticker file_ids from disk."""
    if not SELECTED_ORDER_FILE.exists():
        return []
    try:
        with open(SELECTED_ORDER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []

