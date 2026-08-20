"""
MTProto client wrapper using Telethon.
Creates sticker sets directly from the user account — no _by_bot suffix required.
"""
from pathlib import Path
from typing import List, Optional

from telethon import TelegramClient
from telethon.tl.functions.stickers import (
    CreateStickerSetRequest,
    AddStickerToSetRequest,
)
from telethon.tl.types import (
    InputStickerSetItem,
    InputDocument,
)


SESSION_DIR = Path(".sessions")


def _get_session_path(session_name: str) -> str:
    SESSION_DIR.mkdir(exist_ok=True)
    return str(SESSION_DIR / session_name)


def is_session_authorized(api_id: int, api_hash: str, session_name: str) -> bool:
    """Return True if an existing saved session is already authorized."""
    path = Path(_get_session_path(session_name) + ".session")
    if not path.exists():
        return False
    import asyncio

    async def _check():
        client = TelegramClient(_get_session_path(session_name), api_id, api_hash)
        await client.connect()
        result = await client.is_user_authorized()
        await client.disconnect()
        return result

    try:
        return asyncio.run(_check())
    except Exception:
        return False


class MTProtoStickerClient:
    """Synchronous wrapper around Telethon for sticker set operations."""

    def __init__(self, api_id: int, api_hash: str, session_name: str = "tgstickers"):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_path = _get_session_path(session_name)

    def _make_client(self) -> TelegramClient:
        return TelegramClient(self.session_path, self.api_id, self.api_hash)

    # ------------------------------------------------------------------
    # Sticker set creation
    # ------------------------------------------------------------------
    def create_sticker_set(
        self,
        short_name: str,
        title: str,
        sticker_format: str,
        file_ids_with_emojis: List[tuple],  # [(file_id, [emoji, ...]), ...]
        progress_callback=None,
    ) -> str:
        """
        Create a new sticker set owned by the authenticated user.
        Returns the short name actually registered by Telegram.
        file_ids_with_emojis: list of (telegram_file_id_str, list_of_emoji)
        """
        import asyncio

        async def _run():
            async with self._make_client() as client:
                if not await client.is_user_authorized():
                    raise RuntimeError("Пользователь не авторизован. Сначала войдите в аккаунт.")

                if progress_callback:
                    progress_callback(5, "Получение информации о сессии...")

                me = await client.get_me()

                # Build InputStickerSetItem list — we need InputDocument for each sticker.
                # The file_id from Bot API is NOT the same as MTProto InputDocument.
                # We re-use the Bot API file_id by resolving it via getFile first if needed;
                # but here stickers come from Bot API cache, so we cannot directly inject them.
                # Strategy: upload local thumbnail files by path, or use the resolved URLs.
                # For now we accept local_thumb_path as the upload source.
                # upload_file() returns InputFile, not InputDocument.
                # Send each sticker to Saved Messages to get a real InputDocument, then delete.
                temp_msgs = []
                items = []
                total = len(file_ids_with_emojis)
                for idx, (local_path, emojis) in enumerate(file_ids_with_emojis):
                    if progress_callback:
                        pct = 10 + int((idx / total) * 60)
                        progress_callback(pct, f"Загрузка стикера {idx + 1}/{total}...")
                    emoji_str = "".join(emojis) if emojis else "⭐"
                    msg = await client.send_file(
                        "me",
                        local_path,
                        force_document=True,
                    )
                    temp_msgs.append(msg)
                    items.append(
                        InputStickerSetItem(
                            document=InputDocument(
                                id=msg.document.id,
                                access_hash=msg.document.access_hash,
                                file_reference=msg.document.file_reference,
                            ),
                            emoji=emoji_str,
                        )
                    )
                await client.delete_messages("me", temp_msgs)

                if progress_callback:
                    progress_callback(75, "Отправка запроса на создание стикерпака...")

                result = await client(CreateStickerSetRequest(
                    user_id=me,
                    title=title,
                    short_name=short_name,
                    stickers=items,
                ))

                if progress_callback:
                    progress_callback(100, "Готово!")

                return result.set.short_name

        return asyncio.run(_run())
