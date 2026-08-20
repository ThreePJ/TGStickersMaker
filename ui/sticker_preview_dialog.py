from typing import Optional
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy,
    QWidget
)

from core.models import StickerItem
from utils.emoji_manager import EmojiManager


class StickerPreviewDialog(QDialog):
    """Modal dialog displaying a high-resolution/large preview of a sticker with metadata."""

    def __init__(self, item: StickerItem, parent=None, format_type: Optional[str] = None):
        super().__init__(parent)
        self.item = item
        self.format_type = format_type or getattr(item, "format_type", None)
        self.emoji_mgr = EmojiManager.instance()
        self.setWindowTitle(f"Просмотр стикера {self.item.get_effective_emoji()}")
        self.setModal(True)
        self.setMinimumSize(420, 500)
        self.resize(460, 540)

        # Allow closing with Escape
        QShortcut(QKeySequence("Escape"), self, self.close)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Card Frame for Preview
        frame = QFrame(self)
        frame.setStyleSheet("""
            QFrame {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 16px;
            }
        """)
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(16, 16, 16, 16)
        frame_layout.setAlignment(Qt.AlignCenter)

        # Image preview
        self.image_label = QLabel(frame)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(320, 320)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        if self.item.local_thumb_path and Path(self.item.local_thumb_path).exists():
            pix = QPixmap(self.item.local_thumb_path)
            if not pix.isNull():
                scaled_pix = pix.scaled(
                    340,
                    340,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.image_label.setPixmap(scaled_pix)
            else:
                self._set_text_fallback()
        else:
            self._set_text_fallback()

        frame_layout.addWidget(self.image_label, alignment=Qt.AlignCenter)
        layout.addWidget(frame, stretch=1)

        # Info & Details bar
        info_layout = QHBoxLayout()
        info_layout.setSpacing(10)

        # Emoji section
        lbl_emoji_title = QLabel("<b>Эмодзи:</b>", self)
        lbl_emoji_title.setStyleSheet("color: #cdd6f4; font-size: 13px;")
        info_layout.addWidget(lbl_emoji_title)

        emojis = self.item.get_effective_emoji_list()
        self.emoji_mgr.prefetch_emojis(emojis)

        for emo in emojis:
            emo_lbl = QLabel(self)
            emo_lbl.setFixedSize(22, 22)
            pix = self.emoji_mgr.get_emoji_pixmap(emo, size=20)
            if pix:
                emo_lbl.setPixmap(pix)
            else:
                emo_lbl.setText(emo)
                emo_lbl.setStyleSheet("font-size: 16px;")
            emo_lbl.setToolTip(emo)
            info_layout.addWidget(emo_lbl)

        sep1 = QLabel("•", self)
        sep1.setStyleSheet("color: #45475a; font-size: 14px; font-weight: bold;")
        info_layout.addWidget(sep1)

        # Format info
        fmt = (self.format_type or "static").lower()
        if fmt == "video":
            fmt_text = "🎬 Видео (WEBM)"
            fmt_style = "background-color: rgba(249, 226, 175, 0.15); color: #f9e2af; border: 1px solid #fab387;"
        elif fmt == "animated":
            fmt_text = "✨ Анимация (TGS)"
            fmt_style = "background-color: rgba(203, 166, 247, 0.15); color: #cba6f7; border: 1px solid #cba6f7;"
        else:
            fmt_text = "🖼 Статичный (WEBP)"
            fmt_style = "background-color: rgba(137, 180, 250, 0.15); color: #89b4fa; border: 1px solid #89b4fa;"

        lbl_format = QLabel(fmt_text, self)
        lbl_format.setStyleSheet(f"""
            QLabel {{
                {fmt_style}
                border-radius: 6px;
                padding: 2px 8px;
                font-size: 12px;
                font-weight: bold;
            }}
        """)
        info_layout.addWidget(lbl_format)

        sep2 = QLabel("•", self)
        sep2.setStyleSheet("color: #45475a; font-size: 14px; font-weight: bold;")
        info_layout.addWidget(sep2)

        # Selection status
        status_color = '#a6e3a1' if self.item.is_selected else '#6c7086'
        status_text = 'Выбран' if self.item.is_selected else 'Не выбран'
        status_label = QLabel(f"<b>Статус:</b> <span style='color: {status_color}; font-weight: bold;'>{status_text}</span>", self)
        status_label.setStyleSheet("color: #cdd6f4; font-size: 13px;")
        info_layout.addWidget(status_label)

        info_layout.addStretch()

        btn_close = QPushButton("Закрыть", self)
        btn_close.setObjectName("SecondaryButton")
        btn_close.setMinimumWidth(90)
        btn_close.setStyleSheet("padding: 5px 12px; min-height: 28px; border-radius: 6px;")
        btn_close.clicked.connect(self.accept)
        info_layout.addWidget(btn_close)

        layout.addLayout(info_layout)

    def _set_text_fallback(self):
        emoji = self.item.get_effective_emoji()
        self.image_label.setText(emoji)
        self.image_label.setStyleSheet("font-size: 80px; color: #89b4fa;")
