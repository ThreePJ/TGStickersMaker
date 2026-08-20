DARK_THEME_QSS = """
/* ═══════════════════════════════════════════════
   TGStickers — Catppuccin Mocha Dark Theme
   ═══════════════════════════════════════════════ */

/* Global */
QMainWindow, QDialog {
    background-color: #11111b;
    color: #cdd6f4;
    font-family: "Segoe UI", "Segoe UI Emoji", "Noto Color Emoji", "Apple Color Emoji", Arial, sans-serif;
    font-size: 13px;
}

QWidget {
    background-color: transparent;
    color: #cdd6f4;
}

/* Tooltips */
QToolTip {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #45475a;
    padding: 5px 10px;
    border-radius: 6px;
    font-size: 12px;
}

/* ─── Panels ─── */
QFrame#TopPanel {
    background-color: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 10px;
}

QFrame#BottomPanel {
    background-color: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 10px;
}

QFrame#SidebarFrame {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 10px;
}

/* ─── Splitter ─── */
QSplitter::handle {
    background-color: transparent;
    width: 6px;
}

QSplitter::handle:hover {
    background-color: #45475a;
    border-radius: 3px;
}

/* ─── Sidebar Pack List ─── */
QListWidget#PackSidebarList {
    background-color: transparent;
    border: none;
    outline: none;
    padding: 2px;
}

QListWidget#PackSidebarList::item {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 8px;
    padding: 8px 10px;
    margin-bottom: 6px;
    font-size: 13px;
    font-weight: 500;
}

QListWidget#PackSidebarList::item:hover {
    background-color: #313244;
    border-color: #45475a;
    color: #f5e0dc;
}

QListWidget#PackSidebarList::item:selected {
    background-color: #2a2b3d;
    border: 1px solid #89b4fa;
    color: #89b4fa;
    font-weight: 600;
}

/* ─── ScrollArea & ScrollBars ─── */
QScrollArea {
    border: none;
    background-color: #181825;
    border-radius: 8px;
}

QScrollBar:vertical {
    background-color: transparent;
    width: 8px;
    margin: 2px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #45475a;
    min-height: 30px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #585b70;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
    height: 0px;
}

QScrollBar:horizontal {
    background-color: transparent;
    height: 8px;
    margin: 2px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background-color: #45475a;
    min-width: 30px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #585b70;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: transparent;
    width: 0px;
}

/* ─── Tabs ─── */
QTabWidget::pane {
    border: 1px solid #313244;
    background-color: #181825;
    border-radius: 10px;
    top: -1px;
}

QTabBar::tab {
    background-color: #181825;
    color: #6c7086;
    padding: 8px 18px;
    margin-right: 3px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    border: 1px solid transparent;
    border-bottom: none;
    font-weight: 500;
    font-size: 12px;
}

QTabBar::tab:selected {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-bottom: 2px solid #89b4fa;
}

QTabBar::tab:hover:!selected {
    background-color: #1e1e2e;
    color: #a6adc8;
}

QTabBar::close-button {
    subcontrol-position: right;
    margin-left: 4px;
    padding: 3px;
    border-radius: 4px;
}

QTabBar::close-button:hover {
    background-color: #45475a;
}

/* ─── Buttons ─── */
QPushButton {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 8px;
    padding: 6px 16px;
    font-weight: 500;
    font-size: 13px;
    outline: none;
    min-height: 18px;
}

QPushButton:hover {
    background-color: #313244;
    border-color: #45475a;
}

QPushButton:pressed {
    background-color: #45475a;
}

QPushButton:disabled {
    background-color: #11111b;
    color: #45475a;
    border-color: #1e1e2e;
}

QPushButton#PrimaryButton {
    background-color: #89b4fa;
    color: #11111b;
    border: none;
    font-weight: 700;
    font-size: 13px;
    padding: 8px 20px;
    border-radius: 8px;
}

QPushButton#PrimaryButton:hover {
    background-color: #b4d0fb;
}

QPushButton#PrimaryButton:pressed {
    background-color: #74a8f8;
}

QPushButton#PrimaryButton:disabled {
    background-color: #313244;
    color: #585b70;
}

QPushButton#SettingsButton {
    background-color: transparent;
    color: #a6adc8;
    border: 1px solid #313244;
    padding: 6px 14px;
    font-size: 13px;
}

QPushButton#SettingsButton:hover {
    background-color: #1e1e2e;
    border-color: #45475a;
    color: #cdd6f4;
}

/* ─── LineEdit & PlainTextEdit ─── */
QLineEdit, QPlainTextEdit, QTextEdit {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: #89b4fa;
    selection-color: #11111b;
}

QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {
    border: 1px solid #89b4fa;
}

QLineEdit:disabled {
    background-color: #11111b;
    color: #45475a;
}

/* ─── ComboBox ─── */
QComboBox {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 8px;
    padding: 7px 14px;
    min-height: 18px;
    font-size: 13px;
}

QComboBox:hover {
    border-color: #45475a;
}

QComboBox:focus {
    border-color: #89b4fa;
}

QComboBox::drop-down {
    border: none;
    width: 28px;
}

QComboBox QAbstractItemView {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 8px;
    selection-background-color: #313244;
    selection-color: #cdd6f4;
    outline: none;
    padding: 4px;
}

QComboBox QAbstractItemView::item {
    padding: 6px 12px;
    border-radius: 4px;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #313244;
}

/* ─── CheckBox ─── */
QCheckBox {
    spacing: 6px;
    color: #cdd6f4;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 2px solid #45475a;
    background-color: transparent;
}

QCheckBox::indicator:hover {
    border-color: #89b4fa;
}

QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}

/* ─── ProgressBar ─── */
QProgressBar {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 8px;
    text-align: center;
    color: #cdd6f4;
    font-weight: 600;
    font-size: 11px;
    min-height: 14px;
    max-height: 14px;
}

QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 7px;
}

/* ─── Labels ─── */
QLabel {
    color: #cdd6f4;
}

/* ─── Badges ─── */
QLabel#BadgeStatic {
    background-color: #1e3a5f;
    color: #89b4fa;
    padding: 3px 10px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 11px;
}

QLabel#BadgeAnimated {
    background-color: #3b1f5e;
    color: #cba6f7;
    padding: 3px 10px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 11px;
}

QLabel#BadgeVideo {
    background-color: #4a2c17;
    color: #fab387;
    padding: 3px 10px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 11px;
}

/* ─── Sticker Cards ─── */
QFrame#StickerCard {
    background-color: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 10px;
}

QFrame#StickerCard:hover {
    border-color: #45475a;
    background-color: #232336;
}

QFrame#StickerCardSelected {
    background-color: #1e2a3f;
    border: 2px solid #89b4fa;
    border-radius: 10px;
}

QFrame#StickerCardSelected:hover {
    background-color: #243350;
}

/* Card emoji input */
QFrame#StickerCard QLineEdit,
QFrame#StickerCardSelected QLineEdit {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 2px 4px;
    font-size: 14px;
    min-height: 16px;
}

QFrame#StickerCard QLineEdit:focus,
QFrame#StickerCardSelected QLineEdit:focus {
    border: 1px solid #45475a;
    background-color: #181825;
}

/* ─── Context Menu (QMenu) ─── */
QMenu {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 8px;
    padding: 6px;
}

QMenu::item {
    background-color: transparent;
    color: #cdd6f4;
    padding: 7px 24px 7px 12px;
    border-radius: 6px;
    font-size: 13px;
    margin: 2px 0px;
}

QMenu::item:selected {
    background-color: #313244;
    color: #f5e0dc;
}

QMenu::item:disabled {
    color: #585b70;
}

QMenu::separator {
    height: 1px;
    background-color: #313244;
    margin: 4px 6px;
}

/* ─── MessageBox ─── */
QMessageBox {
    background-color: #1e1e2e;
}

QMessageBox QLabel {
    color: #cdd6f4;
    font-size: 13px;
}

QMessageBox QPushButton {
    min-width: 80px;
}
"""
