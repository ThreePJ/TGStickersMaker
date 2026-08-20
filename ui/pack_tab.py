from typing import List, Optional
from PySide6.QtCore import Qt, Signal, QPoint, QRect, QSize
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QScrollArea,
    QLayout,
    QLayoutItem,
    QSizePolicy,
)

from core.models import StickerPackData, StickerItem
from ui.sticker_card import StickerCard


class FlowLayout(QLayout):
    """
    Standard Qt FlowLayout that automatically wraps child items to fit available width
    and dynamically recalculates required height on resize.
    """

    def __init__(self, parent=None, margin=15, h_spacing=12, v_spacing=15, spacing: Optional[int] = None):
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        if spacing is not None:
            self.h_spacing = spacing
            self.v_spacing = spacing
        else:
            self.h_spacing = h_spacing
            self.v_spacing = v_spacing
        self.itemList: List[QLayoutItem] = []

    def __del__(self):
        if not hasattr(self, 'itemList'):
            return
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item: QLayoutItem):
        self.itemList.append(item)

    def count(self) -> int:
        return len(self.itemList)

    def itemAt(self, index: int) -> Optional[QLayoutItem]:
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index: int) -> Optional[QLayoutItem]:
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientations:
        return Qt.Orientations(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        margins = self.contentsMargins()
        effective_rect = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0

        for item in self.itemList:
            wid = item.widget()
            if wid is not None:
                item_size = wid.sizeHint()
                min_s = wid.minimumSize()
                max_s = wid.maximumSize()
                w = max(item_size.width(), min_s.width()) if min_s.width() > 0 else item_size.width()
                h = max(item_size.height(), min_s.height()) if min_s.height() > 0 else item_size.height()
                if max_s.width() < 16777215:
                    w = min(w, max_s.width())
                if max_s.height() < 16777215:
                    h = min(h, max_s.height())
                item_size = QSize(w, h)
            else:
                item_size = item.sizeHint()

            item_w = item_size.width()
            item_h = item_size.height()

            next_x = x + item_w + self.h_spacing
            if next_x - self.h_spacing > effective_rect.right() and line_height > 0:
                x = effective_rect.x()
                y = y + line_height + self.v_spacing
                next_x = x + item_w + self.h_spacing
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item_size))

            x = next_x
            line_height = max(line_height, item_h)

        return y + line_height - rect.y() + margins.bottom()

class FlowAreaWidget(QWidget):
    """A wrapper widget that forces QScrollArea to recognize FlowLayout's wrapped height."""
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.layout():
            h = self.layout().heightForWidth(self.width())
            self.setMinimumHeight(h)

class PackTab(QWidget):
    """Tab representing a single sticker pack with a toolbar and scrollable grid."""

    selection_changed = Signal()

    def __init__(self, pack_data: StickerPackData, parent=None):
        super().__init__(parent)
        self.pack_data = pack_data
        self.cards: List[StickerCard] = []
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # 1. Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        # Format Badge
        self.badge_label = QLabel(self)
        fmt = self.pack_data.format_type.lower()
        if fmt == "static":
            self.badge_label.setText("  Static  ")
            self.badge_label.setObjectName("BadgeStatic")
        elif fmt == "animated":
            self.badge_label.setText("  Animated  ")
            self.badge_label.setObjectName("BadgeAnimated")
        else:
            self.badge_label.setText("  Video  ")
            self.badge_label.setObjectName("BadgeVideo")
        toolbar.addWidget(self.badge_label)

        # Pack Title & Short Name
        title_label = QLabel(f"<b>{self.pack_data.title}</b> ({self.pack_data.name})", self)
        title_label.setStyleSheet("font-size: 14px; color: #cdd6f4;")
        toolbar.addWidget(title_label)

        toolbar.addStretch()

        # Selection Count
        self.count_label = QLabel("Выбрано: 0 / 0", self)
        self.count_label.setStyleSheet("color: #a6adc8; font-weight: 500;")
        toolbar.addWidget(self.count_label)

        # Action Buttons
        self.btn_select_all = QPushButton("Выбрать все", self)
        self.btn_select_all.clicked.connect(self.select_all)
        toolbar.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("Снять выделение", self)
        self.btn_deselect_all.clicked.connect(self.deselect_all)
        toolbar.addWidget(self.btn_deselect_all)

        main_layout.addLayout(toolbar)

        # 2. Scroll Area for Stickers
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.grid_widget = FlowAreaWidget()
        self.flow_layout = FlowLayout(self.grid_widget, margin=15, h_spacing=15, v_spacing=18)
        self.scroll_area.setWidget(self.grid_widget)
        main_layout.addWidget(self.scroll_area)

        # Create cards
        for item in self.pack_data.stickers:
            card = StickerCard(item, self)
            card.selection_changed.connect(self._on_card_selection_changed)
            self.cards.append(card)
            self.flow_layout.addWidget(card)

        self._update_counter()

    def _on_card_selection_changed(self, _):
        self._update_counter()
        self.selection_changed.emit()

    def _update_counter(self):
        selected_count = sum(1 for c in self.cards if c.item.is_selected)
        total_count = len(self.cards)
        self.count_label.setText(f"Выбрано: {selected_count} / {total_count}")

    def select_all(self):
        for card in self.cards:
            card.set_selected(True)
        self._update_counter()
        self.selection_changed.emit()

    def deselect_all(self):
        for card in self.cards:
            card.set_selected(False)
        self._update_counter()
        self.selection_changed.emit()

    def get_selected_stickers(self) -> List[StickerItem]:
        return [c.item for c in self.cards if c.item.is_selected]

    def get_format_type(self) -> str:
        return self.pack_data.format_type
