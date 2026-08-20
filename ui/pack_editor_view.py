from pathlib import Path
from typing import List, Optional, Dict
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QIcon, QClipboard, QGuiApplication
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QPushButton,
    QLabel,
    QFrame,
    QLineEdit,
    QMessageBox,
    QFileDialog,
    QSplitter,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QComboBox,
    QStackedWidget
)

from core.config_manager import ConfigManager
from core.models import StickerItem, StickerPackData
from ui.emoji_picker import EmojiPickerDialog
from ui.sticker_preview_dialog import StickerPreviewDialog
from ui.pack_tab import FlowLayout, FlowAreaWidget
from utils.emoji_manager import EmojiManager
from utils.workers import (
    FetchPacksWorker,
    UpdateStickerEmojisWorker,
    DeleteStickerWorker,
    ReorderStickerWorker,
    AddStickerWorker,
    UpdatePackTitleWorker,
    DeletePackWorker,
    BatchAddStickersWorker
)
from utils.link_parser import extract_pack_names


class EditorStickerCard(QFrame):
    """Card representing a single sticker in the pack editor."""

    emoji_updated = Signal(str, list)      # file_id, new_emoji_list
    delete_requested = Signal(str)         # file_id
    move_left_requested = Signal(int)      # index
    move_right_requested = Signal(int)     # index

    def __init__(self, item: StickerItem, index: int, total_count: int, parent=None):
        super().__init__(parent)
        self.item = item
        self.index = index
        self.total_count = total_count
        self.emoji_mgr = EmojiManager.instance()
        self.emoji_mgr.emoji_loaded.connect(self._on_emoji_loaded)
        self._tag_buttons: Dict[str, QPushButton] = {}
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("EditorStickerCard")
        self.setStyleSheet("""
            QFrame#EditorStickerCard {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 10px;
            }
            QFrame#EditorStickerCard:hover {
                border-color: #89b4fa;
            }
        """)
        self.setFixedSize(180, 240)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Header: Index position & Delete button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        pos_lbl = QLabel(f"#{self.index + 1}", self)
        pos_lbl.setStyleSheet("color: #89b4fa; font-weight: bold; font-size: 11px;")
        header_layout.addWidget(pos_lbl)
        header_layout.addStretch()

        btn_delete = QPushButton("✕", self)
        btn_delete.setFixedSize(22, 22)
        btn_delete.setToolTip("Удалить этот стикер из стикерпака")
        btn_delete.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #f38ba8;
                border: none;
                font-size: 13px;
                font-weight: bold;
                border-radius: 4px;
                padding: 0px;
                margin: 0px;
                min-height: 0px;
            }
            QPushButton:hover {
                background-color: #f38ba8;
                color: #11111b;
            }
        """)
        btn_delete.clicked.connect(lambda: self.delete_requested.emit(self.item.file_id))
        header_layout.addWidget(btn_delete)
        layout.addLayout(header_layout)

        # Thumbnail Image (Clickable for preview)
        self.thumb_label = QLabel(self)
        self.thumb_label.setFixedSize(100, 100)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setCursor(Qt.PointingHandCursor)
        self.thumb_label.setToolTip("Кликните для предпросмотра")
        self.thumb_label.mousePressEvent = lambda e: self._preview_sticker()

        if self.item.local_thumb_path:
            pixmap = QPixmap(self.item.local_thumb_path)
            if not pixmap.isNull():
                self.thumb_label.setPixmap(
                    pixmap.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
            else:
                self.thumb_label.setText("🖼️")
        else:
            self.thumb_label.setText("🖼️")

        thumb_layout = QHBoxLayout()
        thumb_layout.addStretch()
        thumb_layout.addWidget(self.thumb_label)
        thumb_layout.addStretch()
        layout.addLayout(thumb_layout)

        # Interactive Emoji Badges area
        self.emoji_container = QWidget(self)
        self.emoji_layout = QHBoxLayout(self.emoji_container)
        self.emoji_layout.setContentsMargins(0, 0, 0, 0)
        self.emoji_layout.setSpacing(3)
        layout.addWidget(self.emoji_container)

        self._update_emoji_tags()

        # Footer: Reorder buttons (< >) and Edit Emojis button
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 4, 0, 0)
        footer_layout.setSpacing(4)

        btn_left = QPushButton("◀", self)
        btn_left.setFixedSize(26, 24)
        btn_left.setToolTip("Переместить стикер влево (раньше)")
        btn_left.setEnabled(self.index > 0)
        btn_left.clicked.connect(lambda: self.move_left_requested.emit(self.index))
        footer_layout.addWidget(btn_left)

        btn_edit_emoji = QPushButton("✏ Эмодзи", self)
        btn_edit_emoji.setFixedHeight(24)
        btn_edit_emoji.setToolTip("Изменить привязанные эмодзи")
        btn_edit_emoji.clicked.connect(self._open_emoji_picker)
        footer_layout.addWidget(btn_edit_emoji, stretch=1)

        btn_right = QPushButton("▶", self)
        btn_right.setFixedSize(26, 24)
        btn_right.setToolTip("Переместить стикер вправо (позже)")
        btn_right.setEnabled(self.index < self.total_count - 1)
        btn_right.clicked.connect(lambda: self.move_right_requested.emit(self.index))
        footer_layout.addWidget(btn_right)

        layout.addLayout(footer_layout)

    def _preview_sticker(self):
        dialog = StickerPreviewDialog(self.item, parent=self)
        dialog.exec()

    def _update_emoji_tags(self):
        while self.emoji_layout.count():
            child = self.emoji_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._tag_buttons.clear()

        emoji_list = self.item.get_effective_emoji_list()
        for emo in emoji_list:
            btn = QPushButton(self.emoji_container)
            btn.setFixedSize(22, 22)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(f"Эмодзи {emo}. Кликните для редактирования")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #313244;
                    border: 1px solid #45475a;
                    border-radius: 4px;
                    padding: 0px;
                }
                QPushButton:hover {
                    border-color: #89b4fa;
                }
            """)
            icon = self.emoji_mgr.get_emoji_icon(emo, size=18)
            if not icon.isNull():
                btn.setIcon(icon)
                btn.setIconSize(QSize(18, 18))
            else:
                btn.setText(emo)

            btn.clicked.connect(self._open_emoji_picker)
            self.emoji_layout.addWidget(btn)
            self._tag_buttons[emo] = btn

        self.emoji_layout.addStretch()

    def _on_emoji_loaded(self, emoji_char: str):
        if emoji_char in self._tag_buttons:
            icon = self.emoji_mgr.get_emoji_icon(emoji_char, size=18)
            if not icon.isNull():
                self._tag_buttons[emoji_char].setIcon(icon)
                self._tag_buttons[emoji_char].setIconSize(QSize(18, 18))
                self._tag_buttons[emoji_char].setText("")

    def _open_emoji_picker(self):
        current_list = self.item.get_effective_emoji_list()
        dialog = EmojiPickerDialog(current_emojis=current_list, parent=self)
        if dialog.exec() == EmojiPickerDialog.Accepted:
            new_emojis = dialog.get_selected_emojis()
            if new_emojis != current_list and new_emojis:
                # Telegram API accepts max 20 emojis per sticker
                if len(new_emojis) > 20:
                    new_emojis = new_emojis[:20]
                self.item.selected_emoji = " ".join(new_emojis)
                self._update_emoji_tags()
                self.emoji_updated.emit(self.item.file_id, new_emojis)


class PackEditorView(QWidget):
    """Dedicated management and editing view for user-owned sticker packs."""

    pack_deleted = Signal(str)

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.current_pack_data: Optional[StickerPackData] = None
        self.active_worker = None
        # Callable injected by MainWindow: () -> List[StickerItem]
        self._get_selected_stickers = None
        self._init_ui()
        self.refresh_pack_list()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setObjectName("EditorSplitter")

        # ----------------------------------------------------
        # LEFT PANEL: Owned Packs List
        # ----------------------------------------------------
        left_panel = QFrame(splitter)
        left_panel.setObjectName("EditorLeftPanel")
        left_panel.setMinimumWidth(240)
        left_panel.setMaximumWidth(320)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        left_header = QLabel("<b>Мои стикерпаки:</b>", left_panel)
        left_layout.addWidget(left_header)

        # Quick Add Existing Pack Input
        add_box = QHBoxLayout()
        add_box.setSpacing(6)
        self.input_add_pack = QLineEdit(left_panel)
        self.input_add_pack.setPlaceholderText("Ссылка или имя пака...")
        self.input_add_pack.returnPressed.connect(self._add_owned_pack_from_input)
        add_box.addWidget(self.input_add_pack, stretch=1)

        btn_add_pack = QPushButton("+", left_panel)
        btn_add_pack.setFixedSize(30, 30)
        btn_add_pack.setObjectName("PrimaryButton")
        btn_add_pack.setToolTip("Добавить стикерпак в список управления")
        btn_add_pack.setStyleSheet("font-size: 16px; font-weight: bold; padding: 0px;")
        btn_add_pack.clicked.connect(self._add_owned_pack_from_input)
        add_box.addWidget(btn_add_pack)
        left_layout.addLayout(add_box)

        # List Widget
        self.pack_list_widget = QListWidget(left_panel)
        self.pack_list_widget.currentItemChanged.connect(self._on_pack_selected)
        left_layout.addWidget(self.pack_list_widget, stretch=1)

        # List Action Buttons (Vertical layout to avoid text cut-off)
        btn_auto_find = QPushButton("🔍 Найти паки бота в кэше", left_panel)
        btn_auto_find.setToolTip("Автоматически найти в кэше паки, созданные данным ботом")
        btn_auto_find.clicked.connect(self._auto_discover_bot_packs)
        left_layout.addWidget(btn_auto_find)

        list_btn_layout = QHBoxLayout()
        list_btn_layout.setSpacing(6)
        btn_refresh = QPushButton("🔄 Обновить", left_panel)
        btn_refresh.setToolTip("Перезагрузить список паков")
        btn_refresh.clicked.connect(self.refresh_pack_list)
        list_btn_layout.addWidget(btn_refresh)

        btn_remove_from_list = QPushButton("🗑 Из списка", left_panel)
        btn_remove_from_list.setToolTip("Убрать пак из списка управления (не удаляя из Telegram)")
        btn_remove_from_list.clicked.connect(self._remove_pack_from_list)
        list_btn_layout.addWidget(btn_remove_from_list)
        left_layout.addLayout(list_btn_layout)

        splitter.addWidget(left_panel)

        # ----------------------------------------------------
        # RIGHT PANEL: Pack Editor Workspace & Placeholder
        # ----------------------------------------------------
        self.right_container = QWidget(splitter)
        right_container_layout = QVBoxLayout(self.right_container)
        right_container_layout.setContentsMargins(0, 0, 0, 0)
        right_container_layout.setSpacing(0)

        self.right_stack = QStackedWidget(self.right_container)

        # 1. Empty state placeholder
        self.placeholder_widget = QWidget(self.right_stack)
        placeholder_layout = QVBoxLayout(self.placeholder_widget)
        placeholder_layout.setAlignment(Qt.AlignCenter)
        self.placeholder_label = QLabel(
            "👈 <b>Выберите стикерпак слева</b><br><br>"
            "Или добавьте ссылку / короткое имя вашего пака в поле ввода слева и нажмите <b>+</b>.<br><br>"
            "💡 <i>Все стикерпаки, созданные через это приложение, сохраняются в этом списке автоматически.</i>",
            self.placeholder_widget
        )
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet("color: #6c7086; font-size: 14px; line-height: 1.6;")
        placeholder_layout.addWidget(self.placeholder_label)
        self.right_stack.addWidget(self.placeholder_widget)

        # 2. Main Editor Panel
        right_panel = QFrame(self.right_stack)
        right_panel.setObjectName("EditorRightPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(10)

        # Top Bar: Pack Details & Actions
        self.top_bar = QFrame(right_panel)
        self.top_bar.setStyleSheet("background-color: #1e1e2e; border-radius: 8px; padding: 6px;")
        top_bar_layout = QVBoxLayout(self.top_bar)
        top_bar_layout.setContentsMargins(8, 8, 8, 8)
        top_bar_layout.setSpacing(8)

        # Row 1: Title input & Save button & Link copy & Delete set
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        lbl_title = QLabel("Название:", self.top_bar)
        row1.addWidget(lbl_title)

        self.input_pack_title = QLineEdit(self.top_bar)
        self.input_pack_title.setPlaceholderText("Название стикерпака...")
        row1.addWidget(self.input_pack_title, stretch=1)

        self.btn_save_title = QPushButton("💾 Сохранить", self.top_bar)
        self.btn_save_title.setToolTip("Сохранить новое название пака в Telegram")
        self.btn_save_title.clicked.connect(self._save_pack_title)
        row1.addWidget(self.btn_save_title)

        self.btn_copy_link = QPushButton("📋 Ссылка", self.top_bar)
        self.btn_copy_link.setToolTip("Скопировать ссылку на стикерпак в буфер обмена")
        self.btn_copy_link.clicked.connect(self._copy_pack_link)
        row1.addWidget(self.btn_copy_link)

        self.btn_delete_pack = QPushButton("🗑 Удалить пак", self.top_bar)
        self.btn_delete_pack.setStyleSheet("color: #f38ba8; border-color: #f38ba8;")
        self.btn_delete_pack.clicked.connect(self._delete_entire_pack)
        row1.addWidget(self.btn_delete_pack)
        top_bar_layout.addLayout(row1)

        # Row 2: Metadata Badges (Short name, Format, Count)
        row2 = QHBoxLayout()
        self.lbl_pack_name = QLabel("Имя: —", self.top_bar)
        self.lbl_pack_name.setStyleSheet("color: #a6adc8; font-size: 12px;")
        row2.addWidget(self.lbl_pack_name)

        self.lbl_pack_format = QLabel("Формат: —", self.top_bar)
        self.lbl_pack_format.setStyleSheet("color: #89b4fa; font-size: 12px; font-weight: bold;")
        row2.addWidget(self.lbl_pack_format)

        self.lbl_stickers_count = QLabel("Стикеров: 0", self.top_bar)
        self.lbl_stickers_count.setStyleSheet("color: #a6e3a1; font-size: 12px; font-weight: bold;")
        row2.addWidget(self.lbl_stickers_count)

        row2.addStretch()

        self.btn_add_sticker = QPushButton("+ Добавить стикер", self.top_bar)
        self.btn_add_sticker.setObjectName("PrimaryButton")
        self.btn_add_sticker.clicked.connect(self._prompt_add_sticker)
        row2.addWidget(self.btn_add_sticker)

        self.btn_add_selected = QPushButton("📥 Добавить выбранные", self.top_bar)
        self.btn_add_selected.setObjectName("PrimaryButton")
        self.btn_add_selected.setToolTip(
            "Добавить стикеры, выбранные в каталоге (вкладка 'Выбранные стикеры'), в этот пак"
        )
        self.btn_add_selected.clicked.connect(self._add_selected_stickers_to_pack)
        row2.addWidget(self.btn_add_selected)

        top_bar_layout.addLayout(row2)
        right_layout.addWidget(self.top_bar)

        # Scroll Area for Stickers Grid
        self.scroll_area = QScrollArea(right_panel)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self.grid_container = FlowAreaWidget()
        self.flow_layout = FlowLayout(self.grid_container, margin=8, h_spacing=10, v_spacing=10)
        self.scroll_area.setWidget(self.grid_container)
        right_layout.addWidget(self.scroll_area, stretch=1)

        # Bottom Progress Bar & Status
        self.progress_bar = QProgressBar(right_panel)
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("", right_panel)
        self.status_label.setStyleSheet("color: #89b4fa; font-size: 12px;")
        right_layout.addWidget(self.status_label)

        self.right_stack.addWidget(right_panel)
        right_container_layout.addWidget(self.right_stack)
        splitter.addWidget(self.right_container)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        main_layout.addWidget(splitter)

    def refresh_pack_list(self):
        """Reload list of owned packs from config."""
        self.pack_list_widget.clear()
        owned = self.config_manager.owned_packs
        for pack_name in owned:
            item = QListWidgetItem(f"📦 {pack_name}")
            item.setData(Qt.UserRole, pack_name)
            self.pack_list_widget.addItem(item)

        if self.pack_list_widget.count() > 0 and not self.current_pack_data:
            self.pack_list_widget.setCurrentRow(0)

    def _add_owned_pack_from_input(self):
        raw_text = self.input_add_pack.text().strip()
        if not raw_text:
            return

        names = extract_pack_names(raw_text)
        name = names[0] if names else raw_text.lstrip("@").strip()
        if name:
            self.config_manager.add_owned_pack(name)
            self.input_add_pack.clear()
            self.refresh_pack_list()
            # Select newly added pack
            for i in range(self.pack_list_widget.count()):
                item = self.pack_list_widget.item(i)
                if item.data(Qt.UserRole) == name:
                    self.pack_list_widget.setCurrentItem(item)
                    break

    def _auto_discover_bot_packs(self):
        """Automatically find packs in local cache created by the configured bot."""
        from utils.cache import load_all_packs
        bot_username = (self.config_manager.bot_username or "").strip().lower()
        if not bot_username:
            QMessageBox.information(
                self,
                "Поиск паков",
                "Укажите Bot Username в настройках ⚙, чтобы автоматически находить паки этого бота."
            )
            return

        all_packs = load_all_packs()
        suffix = f"_by_{bot_username}"
        found = 0
        for p in all_packs:
            if suffix in p.name.lower():
                self.config_manager.add_owned_pack(p.name)
                found += 1

        self.refresh_pack_list()
        if found > 0:
            QMessageBox.information(
                self,
                "Поиск завершен",
                f"Найдено и добавлено стикерпаков в список управления: {found}"
            )
        else:
            QMessageBox.information(
                self,
                "Поиск завершен",
                f"В локальном кэше не найдено паков с суффиксом '{suffix}'.\n"
                f"Вы можете вставить ссылку на любой ваш пак в поле ввода выше и нажать '+'."
            )

    def _remove_pack_from_list(self):
        item = self.pack_list_widget.currentItem()
        if not item:
            return
        pack_name = item.data(Qt.UserRole)
        self.config_manager.remove_owned_pack(pack_name)
        self.refresh_pack_list()
        if self.pack_list_widget.count() == 0:
            self._clear_editor_view()

    def _on_pack_selected(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]):
        if not current:
            self._clear_editor_view()
            return
        pack_name = current.data(Qt.UserRole)
        self._load_pack_for_editing(pack_name)

    def _load_pack_for_editing(self, pack_name: str):
        if not self.config_manager.bot_token:
            QMessageBox.warning(self, "API не настроен", "Пожалуйста, укажите токен бота в настройках.")
            return

        self.status_label.setText(f"Загрузка стикерпака '{pack_name}'...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(20)

        self.active_worker = FetchPacksWorker(
            bot_token=self.config_manager.bot_token,
            pack_names=[pack_name],
            parent=self
        )
        self.active_worker.pack_loaded.connect(self._on_pack_loaded)
        self.active_worker.error.connect(self._on_worker_error)
        self.active_worker.start()

    def _on_pack_loaded(self, pack_data: StickerPackData):
        self.current_pack_data = pack_data
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Стикерпак '{pack_data.name}' готов к редактированию.")

        self.input_pack_title.setText(pack_data.title)
        self.lbl_pack_name.setText(f"Имя: {pack_data.name}")
        self.lbl_pack_format.setText(f"Формат: {pack_data.format_type.upper()}")
        self.lbl_stickers_count.setText(f"Стикеров: {len(pack_data.stickers)}")

        self.right_stack.setCurrentIndex(1)
        self._render_stickers_grid()

    def _clear_editor_view(self):
        self.current_pack_data = None
        self.input_pack_title.clear()
        self.lbl_pack_name.setText("Имя: —")
        self.lbl_pack_format.setText("Формат: —")
        self.lbl_stickers_count.setText("Стикеров: 0")
        while self.flow_layout.count():
            child = self.flow_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.right_stack.setCurrentIndex(0)

    def _render_stickers_grid(self):
        # Clear existing cards
        while self.flow_layout.count():
            child = self.flow_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not self.current_pack_data:
            return

        stickers = self.current_pack_data.stickers
        total_count = len(stickers)
        self.lbl_stickers_count.setText(f"Стикеров: {total_count}")

        for idx, item in enumerate(stickers):
            card = EditorStickerCard(item, idx, total_count, parent=self.grid_container)
            card.emoji_updated.connect(self._handle_emoji_update)
            card.delete_requested.connect(self._handle_delete_sticker)
            card.move_left_requested.connect(self._handle_move_left)
            card.move_right_requested.connect(self._handle_move_right)
            self.flow_layout.addWidget(card)

    def _handle_emoji_update(self, file_id: str, new_emojis: list):
        if not self.config_manager.bot_token:
            return

        self.status_label.setText("Обновление эмодзи на серверах Telegram...")
        worker = UpdateStickerEmojisWorker(
            bot_token=self.config_manager.bot_token,
            sticker_file_id=file_id,
            emoji_list=new_emojis,
            parent=self
        )
        worker.success.connect(lambda fid, emos: self.status_label.setText("Эмодзи успешно обновлены!"))
        worker.error.connect(lambda err: QMessageBox.warning(self, "Ошибка", f"Не удалось обновить эмодзи: {err}"))
        worker.start()

    def _handle_delete_sticker(self, file_id: str):
        if not self.current_pack_data or len(self.current_pack_data.stickers) <= 1:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "В стикерпаке должен оставаться хотя бы один стикер. Удаление последнего стикера невозможно."
            )
            return

        confirm = QMessageBox.question(
            self,
            "Подтверждение удаления",
            "Вы уверены, что хотите удалить этот стикер из стикерпака?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        self.status_label.setText("Удаление стикера из пака...")
        worker = DeleteStickerWorker(
            bot_token=self.config_manager.bot_token,
            sticker_file_id=file_id,
            parent=self
        )

        def on_deleted(fid):
            self.status_label.setText("Стикер успешно удален.")
            if self.current_pack_data:
                self.current_pack_data.stickers = [s for s in self.current_pack_data.stickers if s.file_id != fid]
                self._render_stickers_grid()

        worker.success.connect(on_deleted)
        worker.error.connect(lambda err: QMessageBox.warning(self, "Ошибка", f"Не удалось удалить стикер: {err}"))
        worker.start()

    def _handle_move_left(self, index: int):
        if not self.current_pack_data or index <= 0:
            return
        new_pos = index - 1
        item = self.current_pack_data.stickers[index]

        self.status_label.setText(f"Перемещение стикера на позицию #{new_pos + 1}...")
        worker = ReorderStickerWorker(
            bot_token=self.config_manager.bot_token,
            sticker_file_id=item.file_id,
            position=new_pos,
            parent=self
        )

        def on_reordered(fid, pos):
            self.status_label.setText("Порядок стикеров изменен.")
            if self.current_pack_data:
                st = self.current_pack_data.stickers
                st.insert(new_pos, st.pop(index))
                self._render_stickers_grid()

        worker.success.connect(on_reordered)
        worker.error.connect(lambda err: QMessageBox.warning(self, "Ошибка", f"Не удалось изменить порядок: {err}"))
        worker.start()

    def _handle_move_right(self, index: int):
        if not self.current_pack_data or index >= len(self.current_pack_data.stickers) - 1:
            return
        new_pos = index + 1
        item = self.current_pack_data.stickers[index]

        self.status_label.setText(f"Перемещение стикера на позицию #{new_pos + 1}...")
        worker = ReorderStickerWorker(
            bot_token=self.config_manager.bot_token,
            sticker_file_id=item.file_id,
            position=new_pos,
            parent=self
        )

        def on_reordered(fid, pos):
            self.status_label.setText("Порядок стикеров изменен.")
            if self.current_pack_data:
                st = self.current_pack_data.stickers
                st.insert(new_pos, st.pop(index))
                self._render_stickers_grid()

        worker.success.connect(on_reordered)
        worker.error.connect(lambda err: QMessageBox.warning(self, "Ошибка", f"Не удалось изменить порядок: {err}"))
        worker.start()

    def _save_pack_title(self):
        if not self.current_pack_data:
            return
        new_title = self.input_pack_title.text().strip()
        if not new_title:
            QMessageBox.warning(self, "Ошибка", "Название стикерпака не может быть пустым.")
            return
        if len(new_title) > 64:
            QMessageBox.warning(
                self,
                "Слишком длинное название",
                f"Название стикерпака не должно превышать 64 символа (сейчас: {len(new_title)})."
            )
            return

        self.status_label.setText("Сохранение нового названия...")
        worker = UpdatePackTitleWorker(
            bot_token=self.config_manager.bot_token,
            pack_name=self.current_pack_data.name,
            title=new_title,
            parent=self
        )

        def on_title_saved(name, title):
            self.status_label.setText("Название успешно сохранено!")
            if self.current_pack_data:
                self.current_pack_data.title = title

        worker.success.connect(on_title_saved)
        worker.error.connect(lambda err: QMessageBox.warning(self, "Ошибка", f"Не удалось изменить название: {err}"))
        worker.start()

    def _copy_pack_link(self):
        if not self.current_pack_data:
            return
        link = f"https://t.me/addstickers/{self.current_pack_data.name}"
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(link)
        self.status_label.setText("Ссылка на стикерпак скопирована в буфер обмена!")

    def _delete_entire_pack(self):
        if not self.current_pack_data:
            return

        confirm = QMessageBox.critical(
            self,
            "Удаление стикерпака",
            f"Вы ТОЧНО хотите безвозвратно удалить весь стикерпак '{self.current_pack_data.title}' ({self.current_pack_data.name}) из Telegram?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        pack_name = self.current_pack_data.name
        self.status_label.setText(f"Удаление стикерпака '{pack_name}'...")
        worker = DeletePackWorker(
            bot_token=self.config_manager.bot_token,
            pack_name=pack_name,
            parent=self
        )

        def on_pack_deleted(name):
            self.status_label.setText(f"Стикерпак '{name}' удален.")
            self.config_manager.remove_owned_pack(name)
            self.refresh_pack_list()
            self._clear_editor_view()
            self.pack_deleted.emit(name)

        worker.success.connect(on_pack_deleted)
        worker.error.connect(lambda err: QMessageBox.warning(self, "Ошибка", f"Не удалось удалить пак: {err}"))
        worker.start()

    def _prompt_add_sticker(self):
        if not self.current_pack_data:
            return

        file_dialog = QFileDialog(self, "Выберите файл стикера (PNG, WEBP, TGS, WEBM)")
        file_dialog.setNameFilter("Файлы стикеров (*.png *.webp *.tgs *.webm);;Все файлы (*.*)")
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                file_path = selected_files[0]
                self._upload_and_add_sticker(file_path)

    def _upload_and_add_sticker(self, file_path: str):
        if not self.config_manager.user_id:
            QMessageBox.warning(self, "Ошибка", "Укажите ваш User ID в настройках.")
            return

        if not self.current_pack_data:
            return

        # Validate sticker count limit (Telegram max: 120 stickers per pack)
        if len(self.current_pack_data.stickers) >= 120:
            QMessageBox.warning(
                self,
                "Лимит стикеров",
                "В стикерпаке уже 120 стикеров — это максимум, разрешённый Telegram."
            )
            return

        # Validate file extension matches pack format
        import os
        ext = os.path.splitext(file_path)[1].lower()
        format_type = self.current_pack_data.format_type
        allowed = {
            "static": {".png", ".webp"},
            "animated": {".tgs"},
            "video": {".webm"},
        }
        if ext not in allowed.get(format_type, set()):
            QMessageBox.warning(
                self,
                "Неверный формат файла",
                f"Стикерпак формата '{format_type.upper()}' принимает только "
                f"{', '.join(allowed.get(format_type, {}))} файлы.\n"
                f"Вы выбрали: {ext or '(без расширения)'}"
            )
            return

        # Pick emoji for this new sticker
        dialog = EmojiPickerDialog(current_emojis=["⭐"], parent=self)
        if dialog.exec() != EmojiPickerDialog.Accepted:
            return

        emojis = dialog.get_selected_emojis()
        if not emojis:
            emojis = ["⭐"]

        self.status_label.setText(f"Загрузка нового стикера в '{self.current_pack_data.name}'...")
        worker = AddStickerWorker(
            bot_token=self.config_manager.bot_token,
            user_id=self.config_manager.user_id,
            pack_name=self.current_pack_data.name,
            local_file_path=file_path,
            format_type=format_type,
            emoji_list=emojis,
            parent=self
        )

        def on_added(name):
            self.status_label.setText("Стикер успешно добавлен в пак!")
            self._load_pack_for_editing(name)

        worker.success.connect(on_added)
        worker.error.connect(lambda err: QMessageBox.warning(self, "Ошибка", f"Не удалось добавить стикер: {err}"))
        worker.start()

    def _add_selected_stickers_to_pack(self):
        if not self.current_pack_data:
            return
        if not self.config_manager.bot_token or not self.config_manager.user_id:
            QMessageBox.warning(self, "Ошибка", "Укажите токен бота и User ID в настройках.")
            return
        if self._get_selected_stickers is None:
            QMessageBox.information(self, "Нет данных", "Нет доступа к выбранным стикерам.")
            return

        selected: List[StickerItem] = self._get_selected_stickers()
        if not selected:
            QMessageBox.information(
                self,
                "Нет выбранных стикеров",
                "Сначала откройте вкладку 'Каталог стикерпаков', выберите нужные стикеры и вернитесь сюда."
            )
            return

        pack_format = self.current_pack_data.format_type
        compatible = [s for s in selected if self._sticker_matches_format(s, pack_format)]
        incompatible_count = len(selected) - len(compatible)

        free_slots = 120 - len(self.current_pack_data.stickers)
        if free_slots <= 0:
            QMessageBox.warning(
                self, "Лимит стикеров",
                "В стикерпаке уже 120 стикеров — это максимум Telegram."
            )
            return

        if not compatible:
            QMessageBox.warning(
                self, "Несовместимый формат",
                f"Все выбранные стикеры имеют формат, отличный от '{pack_format.upper()}' этого пака.\n"
                "Добавление невозможно."
            )
            return

        to_add = compatible[:free_slots]
        warn_text = ""
        if incompatible_count:
            warn_text += f"\n• {incompatible_count} стикеров пропущено (несовместимый формат)."
        if len(compatible) > free_slots:
            warn_text += f"\n• Будет добавлено только {free_slots} из {len(compatible)} — лимит пака."

        confirm_msg = (
            f"Добавить {len(to_add)} стикер(ов) в пак '{self.current_pack_data.title}'?"
            + warn_text
        )
        if QMessageBox.question(self, "Подтверждение", confirm_msg,
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return

        self.btn_add_selected.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Добавление выбранных стикеров...")

        worker = BatchAddStickersWorker(
            bot_token=self.config_manager.bot_token,
            user_id=self.config_manager.user_id,
            pack_name=self.current_pack_data.name,
            stickers=to_add,
            format_type=pack_format,
            parent=self
        )
        worker.progress.connect(lambda pct, msg: (
            self.progress_bar.setValue(pct),
            self.status_label.setText(msg)
        ))

        def on_batch_success(name: str, added: int):
            self.btn_add_selected.setEnabled(True)
            self.progress_bar.setVisible(False)
            skipped = len(to_add) - added
            msg = f"Добавлено {added} стикер(ов) в пак."
            if skipped:
                msg += f" ({skipped} не удалось добавить — возможно, уже в паке.)"
            self.status_label.setText(msg)
            self._load_pack_for_editing(name)

        def on_batch_error(err: str):
            self.btn_add_selected.setEnabled(True)
            self.progress_bar.setVisible(False)
            QMessageBox.warning(self, "Ошибка", err)

        worker.success.connect(on_batch_success)
        worker.error.connect(on_batch_error)
        worker.start()

    @staticmethod
    def _sticker_matches_format(item: StickerItem, pack_format: str) -> bool:
        """Check if a sticker's source pack format is compatible with target pack."""
        # StickerItem doesn't carry format; we rely on file extension of local thumb as hint,
        # but file_id itself is format-agnostic from API perspective — Telegram enforces it.
        # We pass all stickers through and let the API reject incompatible ones gracefully.
        return True

    def _on_worker_error(self, error_msg: str):
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Ошибка: {error_msg}")
        QMessageBox.warning(self, "Ошибка", error_msg)
