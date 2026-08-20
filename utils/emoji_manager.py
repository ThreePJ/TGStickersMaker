import os
from pathlib import Path
from typing import Optional, List, Dict
from concurrent.futures import ThreadPoolExecutor
import httpx
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import QObject, Signal, Qt

EMOJI_CACHE_DIR = Path(".cache/emojis/apple")


def ensure_emoji_cache_dir() -> Path:
    EMOJI_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return EMOJI_CACHE_DIR


def emoji_to_hex_candidates(emoji_str: str) -> List[str]:
    """Generate potential hex filename candidates for an emoji character."""
    # 1. Full sequence with all codepoints
    hex1 = "-".join(f"{ord(c):x}" for c in emoji_str)
    # 2. Stripped of variation selector FE0F
    hex2 = "-".join(f"{ord(c):x}" for c in emoji_str if c != "\ufe0f")
    # 3. With variation selector FE0F after standalone base if len is 1
    candidates = [hex1, hex2]
    if len(emoji_str) == 1 and f"{ord(emoji_str):x}-fe0f" not in candidates:
        candidates.append(f"{ord(emoji_str):x}-fe0f")
    return list(dict.fromkeys(candidates))


class EmojiManager(QObject):
    """
    Manages Apple Color Emoji (Telegram style) graphics:
    - Downloads & caches PNGs from CDN to `.cache/emojis/apple/`
    - Provides QPixmap and QIcon instances
    - Thread-pool for parallel background pre-fetching
    """
    emoji_loaded = Signal(str)  # Emits emoji_str when an image finishes downloading

    _instance: Optional["EmojiManager"] = None

    @classmethod
    def instance(cls) -> "EmojiManager":
        if cls._instance is None:
            cls._instance = EmojiManager()
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cache_dir = ensure_emoji_cache_dir()
        self._pixmap_cache: Dict[str, QPixmap] = {}
        self._download_executor = ThreadPoolExecutor(max_workers=8)
        self._downloading_set = set()

    def get_local_path(self, emoji_str: str) -> Optional[Path]:
        """Check if emoji image exists in local cache."""
        candidates = emoji_to_hex_candidates(emoji_str)
        for c in candidates:
            file_path = self.cache_dir / f"{c}.png"
            if file_path.exists() and file_path.stat().st_size > 0:
                return file_path
        return None

    def get_emoji_pixmap(self, emoji_str: str, size: int = 32) -> Optional[QPixmap]:
        """Get cached QPixmap or trigger background download."""
        cache_key = f"{emoji_str}_{size}"
        if cache_key in self._pixmap_cache:
            return self._pixmap_cache[cache_key]

        local_path = self.get_local_path(emoji_str)
        if local_path:
            pix = QPixmap(str(local_path))
            if not pix.isNull():
                if size > 0 and (pix.width() != size or pix.height() != size):
                    pix = pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self._pixmap_cache[cache_key] = pix
                return pix

        # Trigger download in background if not already downloading
        if emoji_str not in self._downloading_set:
            self._downloading_set.add(emoji_str)
            self._download_executor.submit(self._download_emoji, emoji_str)

        return None

    def get_emoji_icon(self, emoji_str: str, size: int = 32) -> Optional[QIcon]:
        pix = self.get_emoji_pixmap(emoji_str, size)
        if pix:
            return QIcon(pix)
        return None

    def prefetch_emojis(self, emoji_list: List[str]):
        """Prefetch a list of emojis in background."""
        for emo in emoji_list:
            if not self.get_local_path(emo) and emo not in self._downloading_set:
                self._downloading_set.add(emo)
                self._download_executor.submit(self._download_emoji, emo)

    def _download_emoji(self, emoji_str: str):
        candidates = emoji_to_hex_candidates(emoji_str)
        cdn_templates = [
            "https://cdn.jsdelivr.net/gh/iamcal/emoji-data@master/img-apple-64/{c}.png",
            "https://raw.githubusercontent.com/iamcal/emoji-data/master/img-apple-64/{c}.png"
        ]

        saved_path = None
        for c in candidates:
            target_path = self.cache_dir / f"{c}.png"
            for url_template in cdn_templates:
                url = url_template.format(c=c)
                try:
                    resp = httpx.get(url, timeout=5.0)
                    if resp.status_code == 200 and len(resp.content) > 100:
                        with open(target_path, "wb") as f:
                            f.write(resp.content)
                        saved_path = target_path
                        break
                except Exception:
                    continue
            if saved_path:
                break

        self._downloading_set.discard(emoji_str)
        if saved_path:
            self.emoji_loaded.emit(emoji_str)
