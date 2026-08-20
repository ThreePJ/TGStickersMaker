from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx


class TelegramAPIError(Exception):
    """Exception raised when Telegram Bot API returns an error."""
    pass


class TelegramClient:
    """HTTP client for interacting with Telegram Bot API."""

    BASE_URL = "https://api.telegram.org"

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    def get_me(self, bot_token: str) -> Dict[str, Any]:
        """Validate token and get bot information (including username)."""
        url = f"{self.BASE_URL}/bot{bot_token}/getMe"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url)
            data = resp.json()
            if not data.get("ok"):
                error_msg = data.get("description", "Unknown error validating bot token")
                raise TelegramAPIError(f"Ошибка проверки токена: {error_msg}")
            return data["result"]

    def get_sticker_set(self, bot_token: str, name: str) -> Dict[str, Any]:
        """Fetch sticker set metadata by short name."""
        url = f"{self.BASE_URL}/bot{bot_token}/getStickerSet"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json={"name": name})
            data = resp.json()
            if not data.get("ok"):
                error_msg = data.get("description", f"Failed to fetch sticker set '{name}'")
                raise TelegramAPIError(f"Ошибка загрузки стикерпака '{name}': {error_msg}")
            return data["result"]

    def get_file(self, bot_token: str, file_id: str) -> Dict[str, Any]:
        """Get file metadata including file_path on Telegram servers."""
        url = f"{self.BASE_URL}/bot{bot_token}/getFile"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, params={"file_id": file_id})
            data = resp.json()
            if not data.get("ok"):
                error_msg = data.get("description", f"Failed to get file '{file_id}'")
                raise TelegramAPIError(f"Ошибка получения файла: {error_msg}")
            return data["result"]

    def download_file(self, bot_token: str, file_path: str, destination_path: Path) -> Path:
        """Download a file from Telegram servers to local disk."""
        url = f"{self.BASE_URL}/file/bot{bot_token}/{file_path}"
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url)
            resp.raise_for_status()
            with open(destination_path, "wb") as f:
                f.write(resp.content)
        return destination_path

    def create_new_sticker_set(
        self,
        bot_token: str,
        user_id: int,
        name: str,
        title: str,
        sticker_format: str,
        stickers: List[Dict[str, Any]]
    ) -> bool:
        """
        Create a new sticker set.
        stickers: list of dicts like [{"sticker": file_id, "emoji_list": ["👍"]}]
        sticker_format: 'static' | 'animated' | 'video'
        """
        url = f"{self.BASE_URL}/bot{bot_token}/createNewStickerSet"
        payload = {
            "user_id": user_id,
            "name": name,
            "title": title,
            "sticker_format": sticker_format,
            "stickers": stickers
        }
        with httpx.Client(timeout=self.timeout * 2) as client:
            resp = client.post(url, json=payload)
            data = resp.json()
            if not data.get("ok"):
                error_msg = data.get("description", "Unknown error creating sticker pack")
                raise TelegramAPIError(f"Ошибка создания стикерпака: {error_msg}")
            return True

    def add_sticker_to_set(
        self,
        bot_token: str,
        user_id: int,
        name: str,
        sticker: Dict[str, Any]
    ) -> bool:
        """
        Add a sticker to an existing sticker set.
        sticker: dict like {"sticker": file_id, "emoji_list": ["👍"], "format": "static"}
        """
        url = f"{self.BASE_URL}/bot{bot_token}/addStickerToSet"
        payload = {
            "user_id": user_id,
            "name": name,
            "sticker": sticker
        }
        with httpx.Client(timeout=self.timeout * 2) as client:
            resp = client.post(url, json=payload)
            data = resp.json()
            if not data.get("ok"):
                error_msg = data.get("description", f"Failed to add sticker to set '{name}'")
                raise TelegramAPIError(f"Ошибка добавления стикера: {error_msg}")
            return True

    def delete_sticker_from_set(self, bot_token: str, sticker_file_id: str) -> bool:
        """Delete a sticker from a set using its file_id."""
        url = f"{self.BASE_URL}/bot{bot_token}/deleteStickerFromSet"
        payload = {"sticker": sticker_file_id}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload)
            data = resp.json()
            if not data.get("ok"):
                error_msg = data.get("description", "Failed to delete sticker")
                raise TelegramAPIError(f"Ошибка удаления стикера: {error_msg}")
            return True

    def set_sticker_emoji_list(self, bot_token: str, sticker_file_id: str, emoji_list: List[str]) -> bool:
        """Change the list of emoji associated with a sticker."""
        url = f"{self.BASE_URL}/bot{bot_token}/setStickerEmojiList"
        payload = {
            "sticker": sticker_file_id,
            "emoji_list": emoji_list
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload)
            data = resp.json()
            if not data.get("ok"):
                error_msg = data.get("description", "Failed to update sticker emojis")
                raise TelegramAPIError(f"Ошибка изменения эмодзи: {error_msg}")
            return True

    def set_sticker_position_in_set(self, bot_token: str, sticker_file_id: str, position: int) -> bool:
        """Move a sticker to a specific 0-based position in its set."""
        url = f"{self.BASE_URL}/bot{bot_token}/setStickerPositionInSet"
        payload = {
            "sticker": sticker_file_id,
            "position": position
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload)
            data = resp.json()
            if not data.get("ok"):
                error_msg = data.get("description", "Failed to reorder sticker")
                raise TelegramAPIError(f"Ошибка перемещения стикера: {error_msg}")
            return True

    def set_sticker_set_title(self, bot_token: str, name: str, title: str) -> bool:
        """Update the title of a sticker set."""
        url = f"{self.BASE_URL}/bot{bot_token}/setStickerSetTitle"
        payload = {
            "name": name,
            "title": title
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload)
            data = resp.json()
            if not data.get("ok"):
                error_msg = data.get("description", f"Failed to update title of set '{name}'")
                raise TelegramAPIError(f"Ошибка переименования пака: {error_msg}")
            return True

    def delete_sticker_set(self, bot_token: str, name: str) -> bool:
        """Delete an entire sticker set created by the bot."""
        url = f"{self.BASE_URL}/bot{bot_token}/deleteStickerSet"
        payload = {"name": name}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload)
            data = resp.json()
            if not data.get("ok"):
                error_msg = data.get("description", f"Failed to delete sticker set '{name}'")
                raise TelegramAPIError(f"Ошибка удаления стикерпака: {error_msg}")
            return True

    def upload_sticker_file(
        self,
        bot_token: str,
        user_id: int,
        sticker_format: str,
        file_path: Path
    ) -> Dict[str, Any]:
        """Upload a sticker file (PNG/WEBP/TGS/WEBM) and return Telegram File object."""
        url = f"{self.BASE_URL}/bot{bot_token}/uploadStickerFile"
        data = {
            "user_id": user_id,
            "sticker_format": sticker_format
        }
        with open(file_path, "rb") as f:
            files = {"sticker": (file_path.name, f)}
            with httpx.Client(timeout=self.timeout * 2) as client:
                resp = client.post(url, data=data, files=files)
                res_data = resp.json()
                if not res_data.get("ok"):
                    error_msg = res_data.get("description", "Failed to upload sticker file")
                    raise TelegramAPIError(f"Ошибка загрузки файла стикера: {error_msg}")
                return res_data["result"]
