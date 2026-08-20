from typing import List, Optional
from PySide6.QtCore import Qt, Signal, QSize, QPoint, QMimeData, QTimer, QEvent, QObject
from PySide6.QtGui import QPixmap, QIcon, QDrag, QMouseEvent, QCursor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QPushButton,
    QLabel,
    QFrame,
    QMessageBox,
    QSizePolicy
)

from core.models import StickerItem
from ui.emoji_picker import EmojiPickerDialog
from ui.sticker_preview_dialog import StickerPreviewDialog
from ui.pack_tab import FlowLayout, FlowAreaWidget
from utils.emoji_manager import EmojiManager


class SelectedStickerItemWidget(QFrame):
    """Widget representing a single selected sticker with reordering, emoji tags and preview."""

    deselected = Signal(object)      # StickerItem
    emoji_changed = Signal()
    move_requested = Signal(int, int) # from_index, to_index
    move_left = Signal(int)          # index
    move_right = Signal(int)         # index

    def __init__(self, item: StickerItem, pack_title: str, pack_format: str, index: int, total_count: int, parent_view: 'SelectedStickersView', parent=None):
        super().__init__(parent)
        self.item = item
        self.pack_title = pack_title
        self.pack_format = pack_format
        self.index = index
        self.total_count = total_count
        self.parent_view = parent_view
        self._drag_start_pos: Optional[QPoint] = None
        self.emoji_mgr = EmojiManager.instance()
        self.emoji_mgr.emoji_loaded.connect(self._on_emoji_loaded)
        self.setAcceptDrops(True)
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("SelectedStickerCard")
        self.setStyleSheet("""
            QFrame#SelectedStickerCard {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 12px;
            }
            QFrame#SelectedStickerCard:hover {
                border-color: #89b4fa;
                background-color: #24253a;
            }
        """)
        self.setFixedSize(155, 225)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)

        # 1. Top row: Position badge on left, Source & format in middle, Visible Remove button on right
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(4)

        pos_lbl = QLabel(f"#{self.index + 1}", self)
        pos_lbl.setStyleSheet("""
            background-color: #313244;
            color: #89b4fa;
            font-weight: bold;
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 4px;
        """)
        top_layout.addWidget(pos_lbl)

        eff_fmt = self.item.get_effective_format(self.pack_format).lower()
        if eff_fmt == "video":
            fmt_badge = QLabel("🎬", self)
            fmt_badge.setToolTip("Формат: Видео (WEBM)")
            top_layout.addWidget(fmt_badge)
        elif eff_fmt == "animated":
            fmt_badge = QLabel("✨", self)
            fmt_badge.setToolTip("Формат: Анимация (TGS)")
            top_layout.addWidget(fmt_badge)

        pack_lbl = QLabel(self.pack_title[:7] + ("…" if len(self.pack_title) > 7 else ""), self)
        pack_lbl.setStyleSheet("color: #a6adc8; font-size: 10px;")
        pack_lbl.setToolTip(f"Источник: {self.pack_title} ({self.pack_format})")
        top_layout.addWidget(pack_lbl)
        top_layout.addStretch()

        btn_remove = QPushButton("✕", self)
        btn_remove.setFixedSize(22, 22)
        btn_remove.setCursor(Qt.PointingHandCursor)
        btn_remove.setToolTip("Убрать из выбранных")
        btn_remove.setStyleSheet("""
            QPushButton {
                background-color: rgba(243, 139, 168, 0.15);
                color: #f38ba8;
                border: 1px solid rgba(243, 139, 168, 0.35);
                font-weight: bold;
                font-size: 12px;
                line-height: 12px;
                border-radius: 11px;
                padding: 0px;
                margin: 0px;
                min-height: 0px;
            }
            QPushButton:hover {
                background-color: #f38ba8;
                color: #11111b;
                border: 1px solid #f38ba8;
            }
        """)
        btn_remove.clicked.connect(self._on_remove_clicked)
        top_layout.addWidget(btn_remove)
        layout.addLayout(top_layout)

        # 2. Thumbnail Preview Image (Directly on card with breathing room)
        self.thumb_label = QLabel(self)
        self.thumb_label.setFixedSize(125, 105)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setCursor(Qt.PointingHandCursor)
        self.thumb_label.setStyleSheet("background-color: transparent;")
        self.thumb_label.setToolTip("Кликните для предпросмотра (или перетащите мышью для смены порядка)")
        self.thumb_label.mousePressEvent = lambda e: self._preview_sticker()

        if self.item.local_thumb_path:
            pixmap = QPixmap(self.item.local_thumb_path)
            if not pixmap.isNull():
                self.thumb_label.setPixmap(
                    pixmap.scaled(120, 105, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
            else:
                self.thumb_label.setText("🖼️")
        else:
            self.thumb_label.setText("🖼️")

        thumb_layout = QHBoxLayout()
        thumb_layout.setAlignment(Qt.AlignCenter)
        thumb_layout.addWidget(self.thumb_label)
        layout.addLayout(thumb_layout)

        # 2.1 Conversion button if format is video/animated (Option 2)
        if eff_fmt != "static":
            btn_convert = QPushButton("⚡ В статику (WEBP)", self)
            btn_convert.setFixedHeight(20)
            btn_convert.setCursor(Qt.PointingHandCursor)
            btn_convert.setToolTip("Преобразовать стикер в статический WEBP для совместимости")
            btn_convert.setStyleSheet("""
                QPushButton {
                    background-color: rgba(249, 226, 175, 0.15);
                    color: #f9e2af;
                    border: 1px solid #fab387;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: bold;
                    padding: 0 4px;
                    margin: 0;
                    min-height: 0;
                }
                QPushButton:hover {
                    background-color: #fab387;
                    color: #11111b;
                }
            """)
            btn_convert.clicked.connect(self._convert_to_static)
            layout.addWidget(btn_convert)
        elif self.item.format_override == "static" and self.pack_format != "static":
            lbl_converted = QLabel("✓ Преобразован в WEBP", self)
            lbl_converted.setAlignment(Qt.AlignCenter)
            lbl_converted.setStyleSheet("color: #a6e3a1; font-size: 9px; font-weight: bold;")
            layout.addWidget(lbl_converted)

        # 3. Bottom Row: [◀] [Emoji Button] [▶]
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(5)

        btn_left = QPushButton("◀", self)
        btn_left.setFixedSize(26, 26)
        btn_left.setCursor(Qt.PointingHandCursor)
        btn_left.setToolTip("Переместить влево")
        btn_left.setEnabled(self.index > 0)
        btn_left.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                font-size: 10px;
                padding: 0;
                margin: 0;
                min-height: 0;
            }
            QPushButton:hover:enabled {
                background-color: #45475a;
                border-color: #89b4fa;
                color: #89b4fa;
            }
            QPushButton:disabled {
                color: #45475a;
                background-color: transparent;
                border-color: transparent;
            }
        """)
        btn_left.clicked.connect(lambda: self.move_left.emit(self.index))
        bottom_layout.addWidget(btn_left)

        self.btn_emoji = QPushButton(self)
        self.btn_emoji.setFixedHeight(26)
        self.btn_emoji.setCursor(Qt.PointingHandCursor)
        self.btn_emoji.setToolTip("Нажмите, чтобы изменить эмодзи стикера")
        self.btn_emoji.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 500;
                padding: 0 8px;
                margin: 0;
                min-height: 0;
            }
            QPushButton:hover {
                background-color: #45475a;
                border-color: #89b4fa;
            }
        """)
        self._update_emoji_button()
        self.btn_emoji.clicked.connect(self._open_emoji_picker)
        bottom_layout.addWidget(self.btn_emoji, stretch=1)

        btn_right = QPushButton("▶", self)
        btn_right.setFixedSize(26, 26)
        btn_right.setCursor(Qt.PointingHandCursor)
        btn_right.setToolTip("Переместить вправо")
        btn_right.setEnabled(self.index < self.total_count - 1)
        btn_right.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                font-size: 10px;
                padding: 0;
                margin: 0;
                min-height: 0;
            }
            QPushButton:hover:enabled {
                background-color: #45475a;
                border-color: #89b4fa;
                color: #89b4fa;
            }
            QPushButton:disabled {
                color: #45475a;
                background-color: transparent;
                border-color: transparent;
            }
        """)
        btn_right.clicked.connect(lambda: self.move_right.emit(self.index))
        bottom_layout.addWidget(btn_right)

        layout.addLayout(bottom_layout)

    def sizeHint(self) -> QSize:
        return QSize(155, 225)

    def _convert_to_static(self):
        self.item.format_override = "static"
        self.emoji_changed.emit()

    def _update_emoji_button(self):
        emojis = self.item.get_effective_emoji_list()
        self.emoji_mgr.prefetch_emojis(emojis)

        if emojis:
            primary_emo = emojis[0]
            extra_count = f" +{len(emojis)-1}" if len(emojis) > 1 else ""
            icon = self.emoji_mgr.get_emoji_icon(primary_emo, size=16)
            if icon and not icon.isNull():
                self.btn_emoji.setIcon(icon)
                self.btn_emoji.setIconSize(QSize(16, 16))
                self.btn_emoji.setText(extra_count)
            else:
                self.btn_emoji.setIcon(QIcon())
                self.btn_emoji.setText(f"{primary_emo}{extra_count}")
        else:
            self.btn_emoji.setIcon(QIcon())
            self.btn_emoji.setText("✏ Эмодзи")

    def _on_emoji_loaded(self, emoji_char: str):
        emojis = self.item.get_effective_emoji_list()
        if emojis and emojis[0] == emoji_char:
            self._update_emoji_button()

    def _open_emoji_picker(self):
        current_list = self.item.get_effective_emoji_list()
        dialog = EmojiPickerDialog(current_emojis=current_list, parent=self)
        if dialog.exec() == EmojiPickerDialog.Accepted:
            new_emojis = dialog.get_selected_emojis()
            if new_emojis:
                self.item.selected_emoji = " ".join(new_emojis[:20])
                self._update_emoji_button()
                self.emoji_changed.emit()

    def _on_remove_clicked(self):
        self.item.is_selected = False
        self.deselected.emit(self.item)

    def _preview_sticker(self):
        eff_fmt = self.item.get_effective_format(self.pack_format)
        dialog = StickerPreviewDialog(self.item, self, format_type=eff_fmt)
        dialog.exec()

    # --- Drag and Drop Handlers ---
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if not (event.buttons() & Qt.LeftButton) or not self._drag_start_pos:
            return
        if (event.pos() - self._drag_start_pos).manhattanLength() < 10:
            return

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(f"reorder:{self.index}")
        drag.setMimeData(mime_data)

        # Generate drag preview pixmap
        pixmap = self.grab()
        drag.setPixmap(pixmap.scaled(110, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        drag.setHotSpot(QPoint(55, 75))

        if self.parent_view:
            self.parent_view.start_drag_autoscroll()

        try:
            drag.exec(Qt.MoveAction)
        finally:
            if self.parent_view:
                self.parent_view.stop_drag_autoscroll()

        self._drag_start_pos = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasText() and event.mimeData().text().startswith("reorder:"):
            event.acceptProposedAction()
            self.setStyleSheet("""
                QFrame#SelectedStickerCard {
                    background-color: #2b2d42;
                    border: 2px dashed #89b4fa;
                    border-radius: 12px;
                }
            """)

    def dragMoveEvent(self, event):
        if event.mimeData().hasText() and event.mimeData().text().startswith("reorder:"):
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            QFrame#SelectedStickerCard {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 12px;
            }
        """)

    def dropEvent(self, event):
        self.setStyleSheet("""
            QFrame#SelectedStickerCard {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 12px;
            }
        """)
        text = event.mimeData().text()
        if text.startswith("reorder:"):
            try:
                from_idx = int(text.split(":")[1])
                to_idx = self.index
                if from_idx != to_idx:
                    self.move_requested.emit(from_idx, to_idx)
                event.acceptProposedAction()
            except ValueError:
                pass


class SelectedStickersView(QWidget):
    """View and manager for all selected stickers across loaded packs with smooth drag-and-drop auto-scrolling."""

    selection_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_items_with_packs: List[tuple[StickerItem, str, str]] = []
        self._is_dragging = False
        
        # Smooth 60 FPS auto-scroll timer for drag operations
        self._auto_scroll_timer = QTimer(self)
        self._auto_scroll_timer.setInterval(16)
        self._auto_scroll_timer.timeout.connect(self._handle_auto_scroll)
        
        self._init_ui()
        self._render_cards()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Top Control Bar for selected items
        top_bar = QFrame(self)
        top_bar.setStyleSheet("background-color: #181825; border: 1px solid #313244; border-radius: 8px;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(10, 8, 10, 8)
        top_layout.setSpacing(10)

        self.info_label = QLabel("✨ <b>Выбранные стикеры для нового пака:</b> (0 шт.)", self)
        self.info_label.setStyleSheet("font-size: 13px; color: #cdd6f4;")
        top_layout.addWidget(self.info_label)

        hint_label = QLabel("💡 <i>Перетаскивайте стикеры мышкой или используйте ◀ ▶ для смены порядка</i>", self)
        hint_label.setStyleSheet("color: #6c7086; font-size: 11px;")
        top_layout.addWidget(hint_label)

        top_layout.addStretch()

        self.btn_reset_all_emojis = QPushButton("🔄 Сбросить эмодзи", self)
        self.btn_reset_all_emojis.setObjectName("SecondaryButton")
        self.btn_reset_all_emojis.clicked.connect(self._reset_all_emojis)
        top_layout.addWidget(self.btn_reset_all_emojis)

        self.btn_clear_all = QPushButton("🗑️ Очистить весь выбор", self)
        self.btn_clear_all.setObjectName("SecondaryButton")
        self.btn_clear_all.clicked.connect(self._clear_all_selection)
        top_layout.addWidget(self.btn_clear_all)

        main_layout.addWidget(top_bar)

        # Scroll Area for sticker cards grid
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: #11111b; border: 1px solid #313244; border-radius: 10px;")
        self.scroll_area.setAcceptDrops(True)
        self.scroll_area.viewport().setAcceptDrops(True)
        self.scroll_area.viewport().installEventFilter(self)

        self.grid_widget = FlowAreaWidget()
        self.grid_widget.setAcceptDrops(True)
        self.grid_widget.installEventFilter(self)
        self.flow_layout = FlowLayout(self.grid_widget, margin=15, h_spacing=12, v_spacing=18)

        self.scroll_area.setWidget(self.grid_widget)
        main_layout.addWidget(self.scroll_area, stretch=1)

    def start_drag_autoscroll(self):
        self._is_dragging = True
        if not self._auto_scroll_timer.isActive():
            self._auto_scroll_timer.start()

    def stop_drag_autoscroll(self):
        self._is_dragging = False
        self._auto_scroll_timer.stop()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Monitor drag events in scroll area viewport and container to control smooth auto-scroll."""
        event_type = event.type()
        if event_type in (QEvent.DragEnter, QEvent.DragMove):
            if event.mimeData().hasText() and event.mimeData().text().startswith("reorder:"):
                self.start_drag_autoscroll()
                event.acceptProposedAction()
                return True
        elif event_type == QEvent.Drop:
            self.stop_drag_autoscroll()
        return super().eventFilter(watched, event)

    def _handle_auto_scroll(self):
        """Perform proportional, acceleration-based auto-scrolling near top/bottom edges."""
        if not self.isVisible():
            self.stop_drag_autoscroll()
            return

        vp = self.scroll_area.viewport()
        cursor_global = QCursor.pos()
        pos = vp.mapFromGlobal(cursor_global)
        vp_rect = vp.rect()

        # Check if cursor is horizontally aligned with viewport (with margin)
        if pos.x() < -30 or pos.x() > vp_rect.width() + 30:
            return

        margin = 100  # Detection zone height in pixels from top/bottom borders
        v_bar = self.scroll_area.verticalScrollBar()
        if not v_bar or v_bar.maximum() <= 0:
            return

        # Top border auto-scroll
        if -50 <= pos.y() < margin:
            distance_to_edge = margin - pos.y()
            ratio = max(0.0, min(1.0, distance_to_edge / margin))
            # Smooth proportional speed scaling: from 2px up to 26px per tick (60 FPS)
            speed = max(2, int(ratio * ratio * 24) + int(ratio * 4))
            v_bar.setValue(max(v_bar.minimum(), v_bar.value() - speed))

        # Bottom border auto-scroll
        elif vp_rect.height() - margin < pos.y() <= vp_rect.height() + 50:
            distance_to_edge = pos.y() - (vp_rect.height() - margin)
            ratio = max(0.0, min(1.0, distance_to_edge / margin))
            # Smooth proportional speed scaling: from 2px up to 26px per tick (60 FPS)
            speed = max(2, int(ratio * ratio * 24) + int(ratio * 4))
            v_bar.setValue(min(v_bar.maximum(), v_bar.value() + speed))

    def refresh_stickers(self, items_with_packs: List[tuple[StickerItem, str, str]]):
        """Update grid with currently selected stickers."""
        self.selected_items_with_packs = list(items_with_packs)
        self._render_cards()

    def _render_cards(self):
        total = len(self.selected_items_with_packs)
        self.info_label.setText(f"✨ <b>Выбранные стикеры для нового пака:</b> ({total} шт.)")

        # Clear grid
        while self.flow_layout.count():
            child = self.flow_layout.takeAt(0)
            widget = child.widget()
            if widget:
                widget.deleteLater()

        if not self.selected_items_with_packs:
            self.placeholder_label = QLabel(
                "⭐ <b>Вы пока не выбрали ни одного стикера.</b><br><br>"
                "Перейдите во вкладку <b>«📦 Каталог стикерпаков»</b>, выберите понравившиеся стикеры,<br>"
                "а затем вернитесь сюда для настройки эмодзи и создания нового пака!",
                self.grid_widget
            )
            self.placeholder_label.setAlignment(Qt.AlignCenter)
            self.placeholder_label.setStyleSheet("color: #6c7086; font-size: 14px; line-height: 1.6;")
            self.flow_layout.addWidget(self.placeholder_label)
            self.btn_clear_all.setEnabled(False)
            self.btn_reset_all_emojis.setEnabled(False)
            return

        self.btn_clear_all.setEnabled(True)
        self.btn_reset_all_emojis.setEnabled(True)

        for idx, (item, pack_title, pack_format) in enumerate(self.selected_items_with_packs):
            card = SelectedStickerItemWidget(item, pack_title, pack_format, idx, total, self, self.grid_widget)
            card.deselected.connect(self._on_item_deselected)
            card.emoji_changed.connect(self.selection_changed.emit)
            card.move_left.connect(self._move_item_left)
            card.move_right.connect(self._move_item_right)
            card.move_requested.connect(self._reorder_items)
            self.flow_layout.addWidget(card)

    def _move_item_left(self, index: int):
        if index > 0:
            item = self.selected_items_with_packs.pop(index)
            self.selected_items_with_packs.insert(index - 1, item)
            self._render_cards()
            self.selection_changed.emit()

    def _move_item_right(self, index: int):
        if index < len(self.selected_items_with_packs) - 1:
            item = self.selected_items_with_packs.pop(index)
            self.selected_items_with_packs.insert(index + 1, item)
            self._render_cards()
            self.selection_changed.emit()

    def _reorder_items(self, from_idx: int, to_idx: int):
        if 0 <= from_idx < len(self.selected_items_with_packs) and 0 <= to_idx < len(self.selected_items_with_packs):
            item = self.selected_items_with_packs.pop(from_idx)
            self.selected_items_with_packs.insert(to_idx, item)
            self._render_cards()
            self.selection_changed.emit()

    def get_ordered_stickers(self) -> List[StickerItem]:
        """Return selected stickers in current custom user-defined order."""
        return [entry[0] for entry in self.selected_items_with_packs if entry[0].is_selected]

    def _on_item_deselected(self, item: StickerItem):
        item.is_selected = False
        self.selected_items_with_packs = [p for p in self.selected_items_with_packs if p[0] != item]
        self._render_cards()
        self.selection_changed.emit()

    def _clear_all_selection(self):
        confirm = QMessageBox.question(
            self,
            "Очистка выбора",
            "Вы уверены, что хотите снять выбор со всех стикеров?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            for entry in self.selected_items_with_packs:
                entry[0].is_selected = False
            self.selected_items_with_packs.clear()
            self._render_cards()
            self.selection_changed.emit()

    def _reset_all_emojis(self):
        for item, _ in self.selected_items_with_packs:
            item.reset_emojis()
        self._render_cards()
        self.selection_changed.emit()

