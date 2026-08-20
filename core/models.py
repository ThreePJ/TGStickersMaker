from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import re


def extract_emojis(text: str) -> List[str]:
    """Extract individual emoji characters / graphemes from a string."""
    if not text:
        return []
    # Match standard emoji ranges, variation selectors, zero width joiners, skin tones
    emoji_pattern = re.compile(
        r'[\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff\u2b50-\u2b55\u200d\ufe0f]+',
        flags=re.UNICODE
    )
    matches = emoji_pattern.findall(text)
    res = []
    for m in matches:
        # Split individual emojis if glued together
        for char in m:
            if char not in ("\u200d", "\ufe0f") and char.strip():
                res.append(char)
    return res if res else [c for c in text if c.strip()]


@dataclass
class StickerItem:
    file_id: str
    original_emoji: str
    selected_emoji: str
    thumb_file_id: Optional[str]
    local_thumb_path: Optional[str] = None
    is_selected: bool = False
    custom_emojis: List[str] = field(default_factory=list)
    format_override: Optional[str] = None  # e.g., 'static' when converted from video/animated

    def get_effective_format(self, default_format: str = "static") -> str:
        """Return effective format (considering user format override)."""
        return self.format_override if self.format_override else default_format

    def get_effective_emoji_list(self) -> List[str]:
        """Return list of effective emojis (custom assigned or fallback to original)."""
        if self.custom_emojis:
            return self.custom_emojis
        if self.selected_emoji and self.selected_emoji.strip():
            extracted = extract_emojis(self.selected_emoji.strip())
            if extracted:
                return extracted
            return [self.selected_emoji.strip()]
        if self.original_emoji and self.original_emoji.strip():
            extracted = extract_emojis(self.original_emoji.strip())
            if extracted:
                return extracted
            return [self.original_emoji.strip()]
        return ["⭐"]

    def get_effective_emoji(self) -> str:
        """Return primary emoji string."""
        emojis = self.get_effective_emoji_list()
        return emojis[0] if emojis else "⭐"

    def add_emoji(self, emoji_char: str):
        if not self.custom_emojis:
            self.custom_emojis = list(self.get_effective_emoji_list())
        if emoji_char not in self.custom_emojis:
            self.custom_emojis.append(emoji_char)
            self.selected_emoji = "".join(self.custom_emojis)

    def remove_emoji(self, emoji_char: str):
        if not self.custom_emojis:
            self.custom_emojis = list(self.get_effective_emoji_list())
        if emoji_char in self.custom_emojis:
            self.custom_emojis.remove(emoji_char)
            if not self.custom_emojis:
                self.custom_emojis = ["⭐"]
            self.selected_emoji = "".join(self.custom_emojis)

    def reset_emojis(self):
        self.custom_emojis = []
        self.selected_emoji = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_id": self.file_id,
            "original_emoji": self.original_emoji,
            "selected_emoji": self.selected_emoji,
            "custom_emojis": self.custom_emojis,
            "thumb_file_id": self.thumb_file_id,
            "local_thumb_path": self.local_thumb_path,
            "is_selected": self.is_selected,
            "format_override": self.format_override
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StickerItem':
        return cls(
            file_id=data.get("file_id", ""),
            original_emoji=data.get("original_emoji", ""),
            selected_emoji=data.get("selected_emoji", ""),
            thumb_file_id=data.get("thumb_file_id"),
            local_thumb_path=data.get("local_thumb_path"),
            is_selected=data.get("is_selected", False),
            custom_emojis=data.get("custom_emojis", []),
            format_override=data.get("format_override")
        )


@dataclass
class StickerPackData:
    name: str                  # short_name (from link)
    title: str                 # display title
    format_type: str           # "static", "animated", "video"
    stickers: List[StickerItem] = field(default_factory=list)
    downloaded_at: Optional[float] = None  # Unix timestamp for chronological sorting

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "format_type": self.format_type,
            "stickers": [s.to_dict() for s in self.stickers],
            "downloaded_at": self.downloaded_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StickerPackData':
        return cls(
            name=data.get("name", ""),
            title=data.get("title", ""),
            format_type=data.get("format_type", "static"),
            stickers=[StickerItem.from_dict(s) for s in data.get("stickers", [])],
            downloaded_at=data.get("downloaded_at")
        )
