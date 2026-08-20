from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QIcon, QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QWidget,
)

from core.models import StickerItem
from ui.sticker_preview_dialog import StickerPreviewDialog
from utils.emoji_manager import EmojiManager


class StickerCard(QFrame):
    """
    Card representing a single sticker with:
    - Thumbnail preview (QLabel)
    - Telegram Apple Emoji icon (QLabel)
    - Crisp borders on hover/selection (no dimming/backlight)
    """

    selection_changed = Signal(bool)

    def __init__(self, item: StickerItem, parent=None):
        super().__init__(parent)
        self.item = item
        self._is_hovered = False
        
        self.setFixedSize(140, 180)
        self.setCursor(Qt.PointingHandCursor)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.setSpacing(0)

        # Content container
        self.container = QFrame(self)
        self.container.setObjectName("StickerCardContainer")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(8, 8, 8, 8)
        self.container_layout.setSpacing(6)

        # Image Label
        self.preview_label = QLabel(self.container)
        self.preview_label.setFixedSize(116, 110)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("background-color: transparent;")
        self.preview_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._load_pixmap()
        self.container_layout.addWidget(self.preview_label, alignment=Qt.AlignCenter)

        # Emoji Label (Telegram Apple emoji icon)
        self.emoji_label = QLabel(self.container)
        self.emoji_label.setFixedSize(24, 24)
        self.emoji_label.setAlignment(Qt.AlignCenter)
        self.emoji_label.setStyleSheet("background-color: transparent;")
        self.emoji_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._load_emoji()
        self.container_layout.addWidget(self.emoji_label, alignment=Qt.AlignCenter)

        # Connect emoji manager signal to update icon when downloaded
        EmojiManager.instance().emoji_loaded.connect(self._on_emoji_loaded)

        self.layout.addWidget(self.container)

        self._update_ui_state()

    def _load_pixmap(self):
        if self.item.local_thumb_path:
            pix = QPixmap(self.item.local_thumb_path)
            if not pix.isNull():
                scaled_pix = pix.scaled(
                    110,
                    105,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled_pix)
                return

        # Fallback if no preview
        self.preview_label.setText(self.item.original_emoji or "🖼️")
        self.preview_label.setStyleSheet("font-size: 32px; color: #89b4fa; background-color: transparent;")

    def _load_emoji(self):
        emoji_char = self.item.get_effective_emoji()
        if emoji_char:
            pix = EmojiManager.instance().get_emoji_pixmap(emoji_char, size=20)
            if pix and not pix.isNull():
                self.emoji_label.setPixmap(pix)
            else:
                self.emoji_label.setText(emoji_char)
                self.emoji_label.setStyleSheet("font-size: 14px; background-color: transparent;")
        else:
            self.emoji_label.clear()

    def _on_emoji_loaded(self, emoji_char: str):
        if self.item.get_effective_emoji() == emoji_char:
            pix = EmojiManager.instance().get_emoji_pixmap(emoji_char, size=20)
            if pix and not pix.isNull():
                self.emoji_label.setPixmap(pix)

    def _update_ui_state(self):
        if self.item.is_selected:
            if self._is_hovered:
                self.container.setStyleSheet(
                    "QFrame#StickerCardContainer { border: 2px solid #bbf7b6; border-radius: 12px; background-color: #1e1e2e; }"
                )
            else:
                self.container.setStyleSheet(
                    "QFrame#StickerCardContainer { border: 2px solid #a6e3a1; border-radius: 12px; background-color: #1e1e2e; }"
                )
        else:
            if self._is_hovered:
                self.container.setStyleSheet(
                    "QFrame#StickerCardContainer { border: 2px solid #89b4fa; border-radius: 12px; background-color: #1e1e2e; }"
                )
            else:
                self.container.setStyleSheet(
                    "QFrame#StickerCardContainer { border: 2px solid #313244; border-radius: 12px; background-color: #1e1e2e; }"
                )

    def set_selected(self, selected: bool):
        if self.item.is_selected != selected:
            self.item.is_selected = selected
            self._update_ui_state()
            self.selection_changed.emit(selected)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.toggle_selection()
        elif event.button() == Qt.RightButton:
            self.open_preview()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.open_preview()

    def open_preview(self):
        """Open modal dialog with enlarged sticker preview."""
        dialog = StickerPreviewDialog(self.item, self.window())
        dialog.exec()

    def enterEvent(self, event):
        self._is_hovered = True
        self._update_ui_state()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self._update_ui_state()
        super().leaveEvent(event)

    def toggle_selection(self):
        new_state = not self.item.is_selected
        self.item.is_selected = new_state
        self._update_ui_state()
        self.selection_changed.emit(new_state)
