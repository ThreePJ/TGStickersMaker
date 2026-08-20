from typing import List, Optional
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QGridLayout,
    QLabel,
    QFrame
)
from utils.emoji_manager import EmojiManager


TELEGRAM_CATEGORIES = {
    "😀 Смайлы и люди": [
        "😀", "😃", "😄", "😁", "😆", "🥹", "😅", "😂", "🤣",
        "🥲", "☺️", "😊", "😇", "🙂", "🙃", "😉", "😌", "😍",
        "🥰", "😘", "😗", "😙", "😚", "😋", "😛", "😝", "😜",
        "🤪", "🤨", "🧐", "🤓", "😎", "🥸", "🤩", "🥳", "😏",
        "😒", "😞", "😔", "😟", "😕", "🙁", "☹️", "😣", "😖",
        "😫", "😩", "🥺", "😢", "😭", "😮‍💨", "😤", "😠", "😡",
        "🤬", "🤯", "😳", "🥵", "🥶", "😱", "😨", "😰", "😥",
        "😓", "🫣", "🤗", "🫡", "🤔", "🫢", "🤫", "🤥", "😶",
        "😶‍🌫️", "😐", "😑", "🫥", "🫠", "🤤", "😴", "🥱", "😬",
        "😮", "😯", "😲", "😦", "😧", "😵", "😵‍💫", "🤐", "🥴",
        "🤢", "🤮", "🤧", "😷", "🤒", "🤕", "🤑", "🤠", "😈",
        "👿", "👺", "👹", "💀", "☠️", "👻", "👽", "👾", "🤖",
        "💩", "😺", "😸", "😹", "😻", "😼", "😽", "🙀", "😿",
        "😾", "🙈", "🙉", "🙊", "🐵", "👋", "🤚", "🖐️", "✋",
        "🖖", "🫱", "🫲", "🫳", "🫴", "👌", "🤌", "🤏", "✌️",
        "🤞", "🫰", "🤟", "🤘", "🤙", "👈", "👉", "👆", "🖕",
        "👇", "☝️", "🫵", "👍", "👎", "✊", "👊", "🤛", "🤜",
        "👏", "🙌", "🫶", "👐", "🤲", "🤝", "🙏", "✍️", "💅",
        "🤳", "💪", "🦾", "🦿", "🦵", "🦶", "👂", "🦻", "👃",
        "🧠", "🫀", "🫁", "🦷", "🦴", "👀", "👁️", "👅", "👄",
        "🫦", "👶", "👧", "🧒", "👦", "👩", "🧑", "👨"
    ],
    "🐶 Животные": [
        "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐻‍❄️",
        "🐨", "🐯", "🦁", "🐮", "🐷", "🐽", "🐸", "🐔", "🐧",
        "🐦", "🐤", "🐣", "🐥", "🦆", "🦅", "🦉", "🦇", "🐺",
        "🐗", "🐴", "🦄", "🐝", "🪱", "🐛", "🦋", "🐌", "🐞",
        "🐜", "🪰", "🪲", "🪳", "🦟", "🦗", "🕷️", "🕸️", "🦂",
        "🐢", "🐍", "🦎", "🦖", "🦕", "🐙", "🦑", "🦐", "🦞",
        "🦀", "🐡", "🐠", "🐟", "🐬", "🐳", "🐋", "🦈", "🦭",
        "🐊", "🐅", "🐆", "🦓", "🦍", "🦧", "🦣", "🐘", "🦛",
        "🦏", "🐪", "🐫", "🦒", "🦘", "🦬", "🐃", "🐂", "🐄",
        "🐎", "🐖", "🐏", "🐑", "🦙", "🐐", "🦌", "🐕", "🐩"
    ],
    "🍕 Еда и напитки": [
        "🍏", "🍎", "🍐", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓",
        "🫐", "🍈", "🍒", "🍑", "🥭", "🍍", "🥥", "🥝", "🍅",
        "🍆", "🥑", "🥦", "🥬", "🥒", "🌶️", "🫑", "🌽", "🥕",
        "🫒", "🧄", "🧅", "🥔", "🍠", "🥐", "🥯", "🍞", "🥖",
        "🥨", "🧀", "🥚", "🍳", "🧈", "🥞", "🧇", "🥓", "🥩",
        "🍗", "🍖", "🦴", "🌭", "🍔", "🍟", "🍕", "🫓", "🥪",
        "🥙", "🧆", "🌮", "🌯", "🫔", "🥗", "🥘", "🫕", "🥫",
        "🍝", "🍜", "🍲", "🍛", "🍣", "🍱", "🥟", "🦪", "🍤",
        "🍙", "🍚", "🍘", "🍢", "🥠", "🥮", "🍧", "🍨", "🍦",
        "🥧", "🧁", "🍰", "🎂", "🍮", "🍭", "🍬", "🍫", "🍿",
        "🍩", "🍪", "🌰", "🥜", "🍯", "🥛", "☕", "🫖", "🍵",
        "🧃", "🥤", "🧋", "🫗", "🍶", "🍺", "🍻", "🥂", "🍷"
    ],
    "⚽ Активности": [
        "⚽", "🏀", "🏈", "⚾", "🥎", "🎾", "🏐", "🏉", "🥏",
        "🎱", "🪀", "🏓", "🏸", "🏒", "🏑", "🥍", "🏏", "🪃",
        "🥅", "⛳", "🪁", "🏹", "🎣", "🤿", "🥊", "🥋", "🎽",
        "🛹", "🛼", "🛷", "⛸️", "🥌", "🎿", "⛷️", "🏂", "🪂",
        "🏋️‍♀️", "🏋️‍♂️", "🤼‍♀️", "🤼‍♂️", "🤸‍♀️", "🤸‍♂️", "⛹️‍♀️", "⛹️‍♂️", "🤺",
        "🤾‍♀️", "🤾‍♂️", "🏌️‍♀️", "🏌️‍♂️", "🏇", "🧘‍♀️", "🧘‍♂️", "🏄‍♀️", "🏄‍♂️",
        "🏊‍♀️", "🏊‍♂️", "🤽‍♀️", "🤽‍♂️", "🚣‍♀️", "🚣‍♂️", "🧗‍♀️", "🧗‍♂️", "🚵‍♀️",
        "🚵‍♂️", "🚴‍♀️", "🚴‍♂️", "🏆", "🥇", "🥈", "🥉", "🏅", "🎖️",
        "🏵️", "🎗️", "🎫", "🎟️", "🎪", "🤹", "🎭", "🩰", "🎨"
    ],
    "🚀 Путешествия": [
        "🚗", "🚕", "🚙", "🚌", "🚎", "🏎️", "🚓", "🚑", "🚒",
        "🚐", "🛻", "🚚", "🚛", "🚜", "🦯", "🦽", "🦼", "🛴",
        "🚲", "🛵", "🏍️", "🛺", "🚨", "🚔", "🚍", "🚘", "🚖",
        "🚡", "🚠", "🚟", "🚃", "🚋", "🚞", "🚝", "🚄", "🚅",
        "🚈", "🚂", "🚆", "🚇", "🚊", "🚉", "✈️", "🛫", "🛬",
        "🛩️", "💺", "🛰️", "🚀", "🛸", "🚁", "🛶", "⛵", "🚤",
        "🛥️", "🛳️", "⛴️", "🚢", "⚓", "🪝", "⛽", "🚧", "🚦"
    ],
    "💡 Предметы": [
        "💡", "🔦", "🏮", "🪔", "🧱", "🪵", "🛖", "🔥", "📦",
        "📫", "📪", "📬", "📭", "📮", "📯", "📜", "📃", "📄",
        "📑", "🧾", "📊", "📈", "📉", "🗒️", "🗓️", "📅", "📆",
        "📇", "🗃️", "🗳️", "🗄️", "📋", "📁", "📂", "🗂️", "🗞️",
        "📰", "📓", "📕", "📗", "📘", "📙", "📚", "📖", "🔖",
        "🧷", "🔗", "📎", "🖇️", "📐", "📏", "🧮", "📌", "📍",
        "✂️", "🖊️", "🖋️", "✒️", "🖌️", "🖍️", "📝", "✏️", "🔍",
        "🔎", "🔒", "🔓", "🔏", "🔐", "🔑", "🗝️", "🔨", "🪓"
    ],
    "💖 Символы": [
        "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎",
        "❤️‍🔥", "❤️‍🩹", "💔", "❣️", "💕", "💞", "💓", "💗", "💖",
        "💘", "💝", "💟", "☮️", "✝️", "☪️", "🕉️", "☸️", "✡️",
        "🔯", "🕎", "☯️", "☦️", "🛐", "⛎", "♈", "♉", "♊",
        "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓",
        "🆔", "⚛️", "🉑", "☢️", "☣️", "📴", "📳", "🈶", "🈚",
        "🈸", "🈺", "🈷️", "✴️", "❇️", "✳️", "‼️", "⁉️", "❓",
        "❔", "❕", "❗", "❌", "⭕", "🛑", "⛔", "📛", "🚫",
        "💯", "💢", "♨️", "🚷", "🚯", "🚳", "🚱", "🔞", "📵"
    ]
}


class EmojiPickerWidget(QWidget):
    """
    Telegram-style Emoji Picker with exact Apple Color Emoji icons and 9-column grid.
    """
    emoji_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.emoji_mgr = EmojiManager.instance()
        self.current_category = list(TELEGRAM_CATEGORIES.keys())[0]
        self.emoji_buttons: dict[str, QPushButton] = {}
        
        # Connect background loader to update buttons as icons are fetched
        self.emoji_mgr.emoji_loaded.connect(self._on_emoji_image_loaded)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 1. Search Bar
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("🔍 Поиск эмодзи...")
        self.search_input.setFixedHeight(34)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 4px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
        """)
        self.search_input.textChanged.connect(self._on_search_changed)
        layout.addWidget(self.search_input)

        # 2. Category Tabs Bar
        cat_scroll = QScrollArea(self)
        cat_scroll.setFixedHeight(40)
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        cat_scroll.setStyleSheet("background: transparent; border: none;")

        cat_container = QWidget()
        cat_layout = QHBoxLayout(cat_container)
        cat_layout.setContentsMargins(0, 0, 0, 0)
        cat_layout.setSpacing(4)

        self.cat_buttons = {}
        for cat_name in TELEGRAM_CATEGORIES.keys():
            btn = QPushButton(cat_name, cat_container)
            btn.setFixedHeight(30)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, c=cat_name: self._switch_category(c))
            cat_layout.addWidget(btn)
            self.cat_buttons[cat_name] = btn

        cat_layout.addStretch()
        cat_scroll.setWidget(cat_container)
        layout.addWidget(cat_scroll)

        self._update_cat_button_styles()

        # 3. Main Emoji 9-Columns Grid Scroll Area
        self.grid_scroll = QScrollArea(self)
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 8px;
            }
        """)

        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background-color: transparent;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(8, 8, 8, 8)
        self.grid_layout.setSpacing(4)

        self.grid_scroll.setWidget(self.grid_container)
        layout.addWidget(self.grid_scroll, stretch=1)

        self._render_emojis(TELEGRAM_CATEGORIES[self.current_category])

    def _update_cat_button_styles(self):
        for name, btn in self.cat_buttons.items():
            if name == self.current_category:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #313244;
                        color: #89b4fa;
                        border: 1px solid #89b4fa;
                        border-radius: 6px;
                        padding: 2px 10px;
                        font-weight: bold;
                        font-size: 11px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1e1e2e;
                        color: #a6adc8;
                        border: 1px solid #313244;
                        border-radius: 6px;
                        padding: 2px 10px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: #313244;
                        color: #cdd6f4;
                    }
                """)

    def _switch_category(self, cat_name: str):
        self.current_category = cat_name
        self._update_cat_button_styles()
        self.search_input.clear()
        self._render_emojis(TELEGRAM_CATEGORIES.get(cat_name, []))

    def _on_search_changed(self, text: str):
        query = text.strip()
        if not query:
            self._render_emojis(TELEGRAM_CATEGORIES.get(self.current_category, []))
            return

        matches = []
        for cat, emojis in TELEGRAM_CATEGORIES.items():
            for e in emojis:
                if query in e or query in cat:
                    matches.append(e)

        if not matches and len(query) <= 4:
            matches = [query]

        self._render_emojis(matches[:135])

    def _render_emojis(self, emoji_list: List[str]):
        # Clear existing buttons
        self.emoji_buttons.clear()
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Pre-fetch icons in background
        self.emoji_mgr.prefetch_emojis(emoji_list)

        cols = 9  # Exact 9 columns as in Telegram Desktop
        for idx, emoji_char in enumerate(emoji_list):
            row = idx // cols
            col = idx % cols

            btn = QPushButton(self.grid_container)
            btn.setFixedSize(36, 36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(emoji_char)

            icon = self.emoji_mgr.get_emoji_icon(emoji_char, size=28)
            if icon:
                btn.setIcon(icon)
                btn.setIconSize(QSize(28, 28))
            else:
                # Text fallback until image loads
                btn.setText(emoji_char)

            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 6px;
                    padding: 0px;
                    margin: 0px;
                    min-width: 0px;
                    min-height: 0px;
                    font-size: 18px;
                }
                QPushButton:hover {
                    background-color: #313244;
                }
                QPushButton:pressed {
                    background-color: #45475a;
                }
            """)
            btn.clicked.connect(lambda _, e=emoji_char: self.emoji_selected.emit(e))
            self.grid_layout.addWidget(btn, row, col)
            self.emoji_buttons[emoji_char] = btn

    def _on_emoji_image_loaded(self, emoji_char: str):
        btn = self.emoji_buttons.get(emoji_char)
        if btn:
            icon = self.emoji_mgr.get_emoji_icon(emoji_char, size=28)
            if icon:
                btn.setIcon(icon)
                btn.setIconSize(QSize(28, 28))
                btn.setText("")


class EmojiPickerDialog(QDialog):
    """Popup Dialog to pick a Telegram emoji (Apple Style)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор эмодзи Telegram")
        self.resize(400, 480)
        self.setMinimumSize(360, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.picker = EmojiPickerWidget(self)
        self.picker.emoji_selected.connect(self._on_emoji_clicked)
        layout.addWidget(self.picker)

        self.selected_emoji: Optional[str] = None

    def _on_emoji_clicked(self, emoji_char: str):
        self.selected_emoji = emoji_char
        self.accept()
