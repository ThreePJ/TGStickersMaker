import os
import time
import httpx
from typing import List, Optional
from PySide6.QtCore import QThread, Signal
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.models import StickerItem, StickerPackData
from core.telegram_client import TelegramClient, TelegramAPIError
from utils.cache import get_cached_thumb_path, get_target_cache_path


class FetchPacksWorker(QThread):
    """Worker thread for fetching sticker pack metadata and downloading thumbnails."""
    
    pack_loaded = Signal(object)      # StickerPackData
    progress = Signal(int, str)       # percent (0-100), message
    error = Signal(str)               # error message
    finished_all = Signal()

    def __init__(self, bot_token: str, pack_names: List[str], parent=None):
        super().__init__(parent)
        self.bot_token = bot_token
        self.pack_names = pack_names
        self.client = TelegramClient(self.bot_token)
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        total_packs = len(self.pack_names)

        for pack_idx, pack_name in enumerate(self.pack_names):
            if not pack_name:
                continue
            
            if self._is_cancelled:
                break

            self.progress.emit(
                int((pack_idx / total_packs) * 100), 
                f"Получение информации о {pack_name}..."
            )
            
            try:
                pack_info = self.client.get_sticker_set(self.bot_token, pack_name)
                
                # Parse basic info
                title = pack_info.get("title", pack_name)
                
                is_animated = pack_info.get("is_animated", False)
                is_video = pack_info.get("is_video", False)
                
                format_type = "static"
                if is_animated:
                    format_type = "animated"
                elif is_video:
                    format_type = "video"
                
                pack_data = StickerPackData(
                    name=pack_name,
                    title=title,
                    format_type=format_type,
                    downloaded_at=time.time() + (pack_idx * 0.001)
                )
                
                stickers_list = pack_info.get("stickers", [])
                total_stickers = len(stickers_list)
                
                # First pass - create StickerItems
                for s in stickers_list:
                    # Check if it's animated or video
                    if s.get("is_animated", False):
                        pack_data.format_type = "animated"
                    if s.get("is_video", False):
                        pack_data.format_type = "video"
                    
                    file_id = s.get("file_id")
                    emoji = s.get("emoji", "")
                    
                    thumb = s.get("thumbnail") or s.get("thumb")
                    thumb_file_id = thumb.get("file_id") if thumb else file_id
                    
                    item = StickerItem(
                        file_id=file_id,
                        original_emoji=emoji,
                        selected_emoji="",
                        thumb_file_id=thumb_file_id,
                        is_selected=False
                    )
                    pack_data.stickers.append(item)

                # Second pass - Concurrent downloading of thumbnails
                def fetch_thumb(item: StickerItem) -> None:
                    if not item.thumb_file_id:
                        return
                    
                    cached_path = get_cached_thumb_path(item.thumb_file_id)
                    if cached_path:
                        item.local_thumb_path = str(cached_path)
                        return

                    try:
                        f_info = self.client.get_file(self.bot_token, item.thumb_file_id)
                        file_path = f_info.get("file_path")
                        if not file_path:
                            return
                            
                        target_path = get_target_cache_path(item.thumb_file_id, file_path)
                        self.client.download_file(self.bot_token, file_path, target_path)
                        item.local_thumb_path = str(target_path)
                    except Exception:
                        pass

                with ThreadPoolExecutor(max_workers=8) as executor:
                    futures = {executor.submit(fetch_thumb, item): item for item in pack_data.stickers}
                    completed = 0
                    for future in as_completed(futures):
                        completed += 1
                        if completed % 10 == 0 or completed == total_stickers:
                            base_pct = (pack_idx / total_packs) * 100
                            step_pct = (completed / total_stickers) * (100 / total_packs)
                            self.progress.emit(
                                int(base_pct + step_pct),
                                f"Скачивание обложек {pack_name} ({completed}/{total_stickers})..."
                            )

                self.pack_loaded.emit(pack_data)
                
            except Exception as e:
                self.error.emit(f"Ошибка с паком {pack_name}: {str(e)}")
                
        self.progress.emit(100, "Завершено")
        self.finished_all.emit()


class CreatePackWorker(QThread):
    """Worker thread for creating a new sticker pack via Telegram Bot API."""

    progress = Signal(int, str)
    success = Signal(str)             # Sticker pack link (t.me/addstickers/...)
    error = Signal(str)

    def __init__(
        self,
        bot_token: str,
        user_id: int,
        name: str,
        title: str,
        sticker_format: str,
        stickers: List[StickerItem],
        parent=None
    ):
        super().__init__(parent)
        self.bot_token = bot_token
        self.user_id = user_id
        self.name = name
        self.title = title
        self.sticker_format = sticker_format
        self.stickers = stickers
        self.client = TelegramClient()

    def run(self):
        try:
            self.progress.emit(10, "Подготовка списка стикеров для экспорта...")

            formatted_stickers = []
            for item in self.stickers:
                emoji_list = item.get_effective_emoji_list()
                if not emoji_list:
                    emoji_list = ["⭐"]
                formatted_stickers.append({
                    "sticker": item.file_id,
                    "emoji_list": emoji_list
                })

            if not formatted_stickers:
                self.error.emit("Не выбрано ни одного стикера для добавления в пак.")
                return

            self.progress.emit(30, f"Отправка запроса на создание пака '{self.name}'...")

            self.client.create_new_sticker_set(
                bot_token=self.bot_token,
                user_id=self.user_id,
                name=self.name,
                title=self.title,
                sticker_format=self.sticker_format,
                stickers=formatted_stickers
            )

            self.progress.emit(100, "Стикерпак успешно создан!")
            pack_link = f"https://t.me/addstickers/{self.name}"
            self.success.emit(pack_link)

        except TelegramAPIError as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(f"Непредвиденная ошибка при создании пака: {e}")


class CreatePackMTProtoWorker(QThread):
    """Worker thread for creating a sticker pack via MTProto (Telethon) — no _by_bot suffix."""

    progress = Signal(int, str)
    success = Signal(str)   # pack link
    error = Signal(str)

    def __init__(
        self,
        api_id: int,
        api_hash: str,
        session_name: str,
        bot_token: str,
        short_name: str,
        title: str,
        sticker_format: str,
        stickers: List[StickerItem],
        parent=None,
    ):
        super().__init__(parent)
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.bot_token = bot_token
        self.short_name = short_name
        self.title = title
        self.sticker_format = sticker_format
        self.stickers = stickers

    def run(self):
        import tempfile
        from pathlib import Path
        from core.mtproto_client import MTProtoStickerClient
        from core.telegram_client import TelegramClient as BotClient

        try:
            bot = BotClient()
            tmp_dir = Path(tempfile.mkdtemp(prefix="tgstickers_"))

            items_to_upload = []
            total = len(self.stickers)
            for idx, item in enumerate(self.stickers):
                pct = int((idx / total) * 40)
                self.progress.emit(pct, f"Скачивание стикера {idx + 1}/{total}...")
                try:
                    # Download original sticker file (not thumbnail)
                    f_info = bot.get_file(self.bot_token, item.file_id)
                    file_path_on_server = f_info.get("file_path")
                    if not file_path_on_server:
                        continue
                    ext = Path(file_path_on_server).suffix or ".webp"
                    dest = tmp_dir / f"{item.file_id}{ext}"
                    bot.download_file(self.bot_token, file_path_on_server, dest)
                    items_to_upload.append((str(dest), item.get_effective_emoji_list()))
                except Exception as e:
                    self.error.emit(f"Не удалось скачать стикер {idx + 1}: {e}")
                    return

            if not items_to_upload:
                self.error.emit("Нет стикеров для загрузки.")
                return

            client = MTProtoStickerClient(self.api_id, self.api_hash, self.session_name)
            actual_name = client.create_sticker_set(
                short_name=self.short_name,
                title=self.title,
                sticker_format=self.sticker_format,
                file_ids_with_emojis=items_to_upload,
                progress_callback=lambda pct, msg: self.progress.emit(40 + int(pct * 0.6), msg),
            )

            # Cleanup temp files
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

            pack_link = f"https://t.me/addstickers/{actual_name}"
            self.progress.emit(100, "Стикерпак успешно создан!")
            self.success.emit(pack_link)

        except Exception as e:
            self.error.emit(f"Ошибка MTProto: {e}")


class ValidateTokenWorker(QThread):
    """Worker thread to validate bot token and get bot username."""

    success = Signal(str)  # bot_username
    error = Signal(str)

    def __init__(self, bot_token: str, parent=None):
        super().__init__(parent)
        self.bot_token = bot_token
        self.client = TelegramClient()

    def run(self):
        try:
            bot_info = self.client.get_me(self.bot_token)
            username = bot_info.get("username", "")
            if not username:
                self.error.emit("У бота отсутствует username.")
            else:
                self.success.emit(username)
        except TelegramAPIError as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(f"Непредвиденная ошибка: {e}")


class UpdateStickerEmojisWorker(QThread):
    """Worker to update emoji list for a sticker in a set."""

    success = Signal(str, list)  # file_id, new_emoji_list
    error = Signal(str)

    def __init__(self, bot_token: str, sticker_file_id: str, emoji_list: List[str], parent=None):
        super().__init__(parent)
        self.bot_token = bot_token
        self.sticker_file_id = sticker_file_id
        self.emoji_list = emoji_list
        self.client = TelegramClient()

    def run(self):
        try:
            self.client.set_sticker_emoji_list(self.bot_token, self.sticker_file_id, self.emoji_list)
            self.success.emit(self.sticker_file_id, self.emoji_list)
        except Exception as e:
            self.error.emit(str(e))


class DeleteStickerWorker(QThread):
    """Worker to delete a single sticker from a set."""

    success = Signal(str)  # sticker_file_id
    error = Signal(str)

    def __init__(self, bot_token: str, sticker_file_id: str, parent=None):
        super().__init__(parent)
        self.bot_token = bot_token
        self.sticker_file_id = sticker_file_id
        self.client = TelegramClient()

    def run(self):
        try:
            self.client.delete_sticker_from_set(self.bot_token, self.sticker_file_id)
            self.success.emit(self.sticker_file_id)
        except Exception as e:
            self.error.emit(str(e))


class ReorderStickerWorker(QThread):
    """Worker to move a sticker to a new position in a set."""

    success = Signal(str, int)  # file_id, new_position
    error = Signal(str)

    def __init__(self, bot_token: str, sticker_file_id: str, position: int, parent=None):
        super().__init__(parent)
        self.bot_token = bot_token
        self.sticker_file_id = sticker_file_id
        self.position = position
        self.client = TelegramClient()

    def run(self):
        try:
            self.client.set_sticker_position_in_set(self.bot_token, self.sticker_file_id, self.position)
            self.success.emit(self.sticker_file_id, self.position)
        except Exception as e:
            self.error.emit(str(e))


class AddStickerWorker(QThread):
    """Worker to add a sticker (by existing file_id or local file) to an existing pack."""

    success = Signal(str)  # pack_name
    error = Signal(str)

    def __init__(
        self,
        bot_token: str,
        user_id: int,
        pack_name: str,
        sticker_file_id: Optional[str] = None,
        local_file_path: Optional[str] = None,
        format_type: str = "static",
        emoji_list: Optional[List[str]] = None,
        parent=None
    ):
        super().__init__(parent)
        self.bot_token = bot_token
        self.user_id = user_id
        self.pack_name = pack_name
        self.sticker_file_id = sticker_file_id
        self.local_file_path = local_file_path
        self.format_type = format_type
        self.emoji_list = emoji_list or ["⭐"]
        self.client = TelegramClient()

    def run(self):
        try:
            file_id_to_use = self.sticker_file_id
            if self.local_file_path and not file_id_to_use:
                res = self.client.upload_sticker_file(
                    self.bot_token,
                    self.user_id,
                    self.format_type,
                    self.local_file_path
                )
                file_id_to_use = res.get("file_id")

            if not file_id_to_use:
                self.error.emit("Не удалось подготовить стикер для добавления.")
                return

            sticker_obj = {
                "sticker": file_id_to_use,
                "emoji_list": self.emoji_list,
                "format": self.format_type
            }

            self.client.add_sticker_to_set(
                self.bot_token,
                self.user_id,
                self.pack_name,
                sticker_obj
            )
            self.success.emit(self.pack_name)
        except Exception as e:
            self.error.emit(str(e))


class UpdatePackTitleWorker(QThread):
    """Worker to update the title of a sticker pack."""

    success = Signal(str, str)  # pack_name, new_title
    error = Signal(str)

    def __init__(self, bot_token: str, pack_name: str, title: str, parent=None):
        super().__init__(parent)
        self.bot_token = bot_token
        self.pack_name = pack_name
        self.title = title
        self.client = TelegramClient()

    def run(self):
        try:
            self.client.set_sticker_set_title(self.bot_token, self.pack_name, self.title)
            self.success.emit(self.pack_name, self.title)
        except Exception as e:
            self.error.emit(str(e))


class BatchAddStickersWorker(QThread):
    """Add multiple stickers (by file_id) to an existing pack one by one."""

    progress = Signal(int, str)   # percent, message
    success = Signal(str, int)    # pack_name, added_count
    error = Signal(str)

    def __init__(
        self,
        bot_token: str,
        user_id: int,
        pack_name: str,
        stickers: List[StickerItem],
        format_type: str,
        parent=None
    ):
        super().__init__(parent)
        self.bot_token = bot_token
        self.user_id = user_id
        self.pack_name = pack_name
        self.stickers = stickers
        self.format_type = format_type
        self.client = TelegramClient()

    def run(self):
        total = len(self.stickers)
        added = 0
        errors = []
        for i, item in enumerate(self.stickers):
            self.progress.emit(
                int((i / total) * 100),
                f"Добавление стикера {i + 1}/{total}..."
            )
            emoji_list = item.get_effective_emoji_list() or ["⭐"]
            sticker_obj = {
                "sticker": item.file_id,
                "emoji_list": emoji_list,
                "format": self.format_type,
            }
            try:
                self.client.add_sticker_to_set(
                    self.bot_token, self.user_id, self.pack_name, sticker_obj
                )
                added += 1
            except Exception as e:
                errors.append(str(e))

        self.progress.emit(100, "Готово")
        if errors and added == 0:
            self.error.emit(f"Не удалось добавить ни одного стикера:\n{errors[0]}")
        else:
            if errors:
                # partial success — emit success but caller can check added count vs total
                pass
            self.success.emit(self.pack_name, added)


class DeletePackWorker(QThread):
    """Worker to completely delete a sticker set."""

    success = Signal(str)  # pack_name
    error = Signal(str)

    def __init__(self, bot_token: str, pack_name: str, parent=None):
        super().__init__(parent)
        self.bot_token = bot_token
        self.pack_name = pack_name
        self.client = TelegramClient()

    def run(self):
        try:
            self.client.delete_sticker_set(self.bot_token, self.pack_name)
            self.success.emit(self.pack_name)
        except Exception as e:
            self.error.emit(str(e))
