import re
from typing import Dict, List, Optional
from PySide6.QtCore import Qt, QSize, QTimer, QRegularExpression
from PySide6.QtGui import QClipboard, QGuiApplication, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QLabel,
    QLineEdit,
    QComboBox,
    QProgressBar,
    QMessageBox,
    QFrame,
    QApplication,
    QScrollArea,
    QGridLayout,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QSplitter,
    QTabWidget,
    QMenu
)

from core.config_manager import ConfigManager
from core.models import StickerPackData, StickerItem
from utils.workers import FetchPacksWorker, CreatePackWorker, CreatePackMTProtoWorker
from utils.cache import (
    load_all_packs,
    save_pack,
    delete_pack_from_cache,
    save_selected_order,
    load_selected_order
)
from ui.pack_tab import PackTab
from ui.settings_dialog import SettingsDialog
from ui.selected_stickers_view import SelectedStickersView
from ui.pack_editor_view import PackEditorView
from ui.mtproto_auth_dialog import MTProtoAuthDialog


class MainWindow(QMainWindow):
    """Main window for TGStickers application."""

    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.pack_tabs: Dict[str, PackTab] = {}
        self.pack_list_items: Dict[str, QListWidgetItem] = {}
        self.fetch_worker: Optional[FetchPacksWorker] = None
        self.create_worker: Optional[CreatePackWorker] = None
        self.packs: list[StickerPackData] = []
        
        self._init_ui()
        self._load_cached_packs()

    def _init_ui(self):
        self.setWindowTitle("TGStickers — Telegram Sticker Pack Merger & Collector")
        self.resize(1100, 800)
        self.setMinimumSize(900, 650)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # ----------------------------------------------------
        # 1. TOP PANEL: Links Input and Actions
        # ----------------------------------------------------
        top_frame = QFrame(self)
        top_frame.setObjectName("TopPanel")
        top_layout = QVBoxLayout(top_frame)
        top_layout.setContentsMargins(12, 12, 12, 12)
        top_layout.setSpacing(8)

        top_header_layout = QHBoxLayout()
        header_title = QLabel("<b>Ссылки на стикерпаки:</b> (по одной на строку или через пробел)", self)
        top_header_layout.addWidget(header_title)
        top_header_layout.addStretch()

        self.btn_settings = QPushButton("⚙ Настройки API", self)
        self.btn_settings.clicked.connect(self._open_settings)
        top_header_layout.addWidget(self.btn_settings)

        top_layout.addLayout(top_header_layout)

        input_action_layout = QHBoxLayout()
        input_action_layout.setSpacing(10)

        self.links_input = QPlainTextEdit(self)
        self.links_input.setPlaceholderText(
            "Вставьте ссылки, например:\n"
            "https://t.me/addstickers/pepe_stickers\n"
            "https://t.me/addstickers/cat_memes"
        )
        self.links_input.setFixedHeight(75)
        input_action_layout.addWidget(self.links_input, stretch=1)

        self.btn_fetch = QPushButton("📥 Загрузить паки", self)
        self.btn_fetch.setObjectName("PrimaryButton")
        self.btn_fetch.setMinimumWidth(150)
        self.btn_fetch.setMinimumHeight(75)
        self.btn_fetch.clicked.connect(self._start_fetching_packs)
        input_action_layout.addWidget(self.btn_fetch)

        top_layout.addLayout(input_action_layout)
        main_layout.addWidget(top_frame)

        # ----------------------------------------------------
        # 2. MAIN MODE TABS (1: Catalog/Browser, 2: Selected Stickers Editor)
        # ----------------------------------------------------
        self.mode_tabs = QTabWidget(self)
        self.mode_tabs.currentChanged.connect(self._on_mode_tab_changed)

        # Tab 1 Widget: Catalog (Left Sidebar + Right Active Pack View)
        catalog_widget = QWidget(self)
        catalog_layout = QVBoxLayout(catalog_widget)
        catalog_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal, catalog_widget)
        splitter.setObjectName("MainSplitter")

        # Left Sidebar for sticker packs
        sidebar_frame = QFrame(self)
        sidebar_frame.setObjectName("SidebarFrame")
        sidebar_frame.setMinimumWidth(240)
        sidebar_frame.setMaximumWidth(320)
        sidebar_layout = QVBoxLayout(sidebar_frame)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(8)

        sidebar_header = QLabel("📦 <b>Стикерпаки:</b>", sidebar_frame)
        sidebar_header.setStyleSheet("font-size: 13px; color: #a6adc8; padding: 2px 4px;")
        sidebar_layout.addWidget(sidebar_header)

        self.pack_list_widget = QListWidget(sidebar_frame)
        self.pack_list_widget.setObjectName("PackSidebarList")
        self.pack_list_widget.currentRowChanged.connect(self._on_pack_selected)
        self.pack_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.pack_list_widget.customContextMenuRequested.connect(self._show_pack_context_menu)
        sidebar_layout.addWidget(self.pack_list_widget)

        # Button to remove selected pack from workspace
        self.btn_remove_pack = QPushButton("🗑️ Удалить пак из списка", sidebar_frame)
        self.btn_remove_pack.setObjectName("SecondaryButton")
        self.btn_remove_pack.setEnabled(False)
        self.btn_remove_pack.clicked.connect(self._remove_current_pack)
        sidebar_layout.addWidget(self.btn_remove_pack)

        splitter.addWidget(sidebar_frame)

        # Right Area: QStackedWidget
        self.content_stack = QStackedWidget(self)
        self.content_stack.setObjectName("ContentStack")

        # Placeholder widget when no packs are open
        self.placeholder_widget = QWidget(self)
        placeholder_layout = QVBoxLayout(self.placeholder_widget)
        placeholder_layout.setAlignment(Qt.AlignCenter)
        self.placeholder_label = QLabel(
            "👋 <b>Нет загруженных стикерпаков</b><br><br>"
            "1. Укажите Bot Token в ⚙ <b>Настройках</b>.<br>"
            "2. Вставьте одну или несколько ссылок выше и нажмите <b>Загрузить паки</b>.<br>"
            "3. Выбирайте нужные стикеры слева и создавайте новый объединенный пак!",
            self
        )
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet("color: #6c7086; font-size: 14px; line-height: 1.6;")
        placeholder_layout.addWidget(self.placeholder_label)
        self.content_stack.addWidget(self.placeholder_widget)

        splitter.addWidget(self.content_stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        catalog_layout.addWidget(splitter)
        self.mode_tabs.addTab(catalog_widget, "📦 Каталог стикерпаков (Выбор)")

        # Tab 2 Widget: Selected Stickers Workspace
        self.selected_stickers_view = SelectedStickersView(self)
        self.selected_stickers_view.selection_changed.connect(self._on_selected_view_updated)
        self.mode_tabs.addTab(self.selected_stickers_view, "🎨 Выбранные стикеры (0)")

        # Tab 3 Widget: Owned Pack Editor Workspace
        self.pack_editor_view = PackEditorView(self.config_manager, self)
        self.pack_editor_view._get_selected_stickers = self._get_all_selected_items_flat
        self.mode_tabs.addTab(self.pack_editor_view, "✏ Редактор моих паков")

        main_layout.addWidget(self.mode_tabs, stretch=1)

        # ----------------------------------------------------
        # 3. BOTTOM PANEL: Pack Builder / Exporter
        # ----------------------------------------------------
        self.bottom_frame = QFrame(self)
        self.bottom_frame.setObjectName("BottomPanel")
        bottom_layout = QVBoxLayout(self.bottom_frame)
        bottom_layout.setContentsMargins(12, 12, 12, 12)
        bottom_layout.setSpacing(10)

        # Row 1: Summary counters & format warning
        counters_layout = QHBoxLayout()
        self.summary_label = QLabel("Выбрано стикеров: <b>0</b> (Статика: 0 | Анимация: 0 | Видео: 0)", self)
        self.summary_label.setStyleSheet("font-size: 13px;")
        counters_layout.addWidget(self.summary_label)

        counters_layout.addStretch()

        format_label = QLabel("Формат экспорта:", self)
        counters_layout.addWidget(format_label)

        self.format_combo = QComboBox(self)
        self.format_combo.addItem("🖼️ Статические (static)", "static")
        self.format_combo.addItem("✨ Анимированные (animated)", "animated")
        self.format_combo.addItem("🎥 Видео (video)", "video")
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        counters_layout.addWidget(self.format_combo)

        bottom_layout.addLayout(counters_layout)

        # Warning line for mixed formats or validations
        self.warning_label = QLabel("", self)
        self.warning_label.setStyleSheet("color: #f38ba8; font-weight: bold; font-size: 12px;")
        self.warning_label.setWordWrap(True)
        self.warning_label.hide()
        bottom_layout.addWidget(self.warning_label)

        # Row 2: Target pack title, short_name, and submit button
        inputs_layout = QHBoxLayout()
        inputs_layout.setSpacing(8)

        # Title
        self.title_input = QLineEdit(self)
        self.title_input.setPlaceholderText("Название стикерпака (Title, например: Мои лучшие мемы)")
        self.title_input.textChanged.connect(self._validate_export_inputs)
        inputs_layout.addWidget(self.title_input, stretch=3)

        # Short name
        self.name_input = QLineEdit(self)
        self.name_input.setPlaceholderText("short_name (например: best_memes)")
        # Regex: starts with letter, only a-z, A-Z, 0-9, and _
        rx = QRegularExpression(r"^[a-zA-Z][a-zA-Z0-9_]{0,60}$")
        self.name_input.setValidator(QRegularExpressionValidator(rx, self))
        self.name_input.textChanged.connect(self._validate_export_inputs)
        inputs_layout.addWidget(self.name_input, stretch=2)

        # Create Pack Button (Bot API — adds _by_bot suffix)
        self.btn_create_pack = QPushButton("🚀 Создать (Bot API)", self)
        self.btn_create_pack.setObjectName("PrimaryButton")
        self.btn_create_pack.setFixedHeight(34)
        self.btn_create_pack.setToolTip("Создать стикерпак через Bot API (ссылка будет с _by_botname)")
        self.btn_create_pack.clicked.connect(self._start_creating_pack)
        inputs_layout.addWidget(self.btn_create_pack, stretch=1)

        # Create Pack via MTProto — no _by_bot suffix
        self.btn_create_mtproto = QPushButton("✨ Создать (Аккаунт)", self)
        self.btn_create_mtproto.setFixedHeight(34)
        self.btn_create_mtproto.setToolTip(
            "Создать стикерпак от имени вашего аккаунта (без суффикса _by_bot).\n"
            "Требует авторизации через MTProto."
        )
        self.btn_create_mtproto.clicked.connect(self._start_creating_pack_mtproto)
        inputs_layout.addWidget(self.btn_create_mtproto, stretch=1)

        bottom_layout.addLayout(inputs_layout)

        # Row 3: Progress Bar & Status text
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(10)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
        progress_layout.addWidget(self.progress_bar, stretch=1)

        self.status_label = QLabel("Готов к работе.", self)
        self.status_label.setStyleSheet("color: #a6adc8;")
        progress_layout.addWidget(self.status_label, stretch=2)

        bottom_layout.addLayout(progress_layout)
        main_layout.addWidget(self.bottom_frame)

    def _open_settings(self):
        dialog = SettingsDialog(self.config_manager, self)
        if dialog.exec():
            self._validate_export_inputs()

    # ----------------------------------------------------
    # Fetching Packs
    # ----------------------------------------------------
    def _start_fetching_packs(self):
        if not self.config_manager.bot_token:
            QMessageBox.warning(
                self,
                "Требуется настройка",
                "Перед загрузкой паков укажите Telegram Bot Token в окне настроек ⚙."
            )
            self._open_settings()
            return

        links_text = self.links_input.toPlainText().strip()
        if not links_text:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, вставьте ссылки на стикерпаки.")
            return

        bot_token = self.config_manager.bot_token
        if not bot_token:
            QMessageBox.warning(self, "Ошибка", "Сначала укажите токен бота в настройках.")
            return

        # Извлечение коротких имен паков
        links = re.findall(r'[^\s,]+', links_text)
        pack_names = []
        for ln in links:
            if "t.me/addstickers/" in ln:
                pack_names.append(ln.split("t.me/addstickers/")[-1])
            else:
                pack_names.append(ln)

        # Выявление дубликатов
        loaded_names = {p.name for p in self.packs}
        new_pack_names = [name for name in pack_names if name not in loaded_names]

        if not new_pack_names:
            if pack_names:
                 QMessageBox.information(self, "Информация", "Указанные стикерпаки уже были загружены.")
            return

        self.btn_fetch.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Запуск скачивания...")

        self.fetch_worker = FetchPacksWorker(bot_token, new_pack_names)
        self.fetch_worker.progress.connect(self._on_fetch_progress)
        self.fetch_worker.pack_loaded.connect(self._on_pack_loaded)
        self.fetch_worker.error.connect(self._on_fetch_error)
        self.fetch_worker.finished_all.connect(self._on_fetch_finished)
        self.fetch_worker.start()

    def _on_fetch_progress(self, val: int, msg: str):
        self.progress_bar.setValue(val)
        self.status_label.setText(msg)

    def _on_pack_loaded(self, pack_data: StickerPackData):
        self.packs.append(pack_data)
        save_pack(pack_data)  # Кэшируем загруженный пак
        self._create_tab_for_pack(pack_data)

    def _on_fetch_error(self, err_msg: str):
        self.status_label.setText(f"⚠️ {err_msg}")
        QMessageBox.warning(self, "Ошибка загрузки", err_msg)

    def _on_fetch_finished(self):
        self.btn_fetch.setEnabled(True)
        self.progress_bar.hide()
        self.status_label.setText("Загрузка паков завершена.")
        self.links_input.clear()
        self._update_ui_state()

    def _on_pack_selected(self, row: int):
        if row < 0 or row >= self.pack_list_widget.count():
            self.content_stack.setCurrentWidget(self.placeholder_widget)
            self.btn_remove_pack.setEnabled(False)
            return

        item = self.pack_list_widget.item(row)
        pack_name = item.data(Qt.UserRole)
        tab = self._get_or_create_pack_tab(pack_name)
        if tab:
            self.content_stack.setCurrentWidget(tab)
            self.btn_remove_pack.setEnabled(True)

    def _get_or_create_pack_tab(self, pack_name: str) -> Optional[PackTab]:
        if not pack_name:
            return None
        if pack_name in self.pack_tabs:
            return self.pack_tabs[pack_name]
        
        pack_data = next((p for p in self.packs if p.name == pack_name), None)
        if not pack_data:
            return None

        # Instantiate PackTab lazily on first view
        tab = PackTab(pack_data, self)
        tab.selection_changed.connect(self._on_selection_updated)
        self.pack_tabs[pack_data.name] = tab
        self.content_stack.addWidget(tab)
        return tab

    def _show_pack_context_menu(self, pos):
        item = self.pack_list_widget.itemAt(pos)
        if not item:
            return
        pack_name = item.data(Qt.UserRole)
        if not pack_name:
            return

        pack_data = next((p for p in self.packs if p.name == pack_name), None)
        pack_title = pack_data.title if pack_data else pack_name

        menu = QMenu(self)

        # 1. Copy pack link
        action_copy_link = menu.addAction("📋 Скопировать ссылку на пак")

        menu.addSeparator()

        # 2. Remove from list (session only)
        action_remove = menu.addAction("🗑️ Удалить из списка (только из сессии)")

        # 3. Delete from cache on disk
        action_delete_cache = menu.addAction("🧹 Удалить из кэша на диске (насовсем)")

        selected_action = menu.exec(self.pack_list_widget.mapToGlobal(pos))
        if not selected_action:
            return

        if selected_action == action_copy_link:
            link = f"https://t.me/addstickers/{pack_name}"
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(link)
            self.status_label.setText(f"Ссылка скопирована: {link}")

        elif selected_action == action_remove:
            self._remove_pack_by_name(pack_name, from_cache=False)

        elif selected_action == action_delete_cache:
            reply = QMessageBox.question(
                self,
                "Удаление из кэша",
                f"Вы действительно хотите удалить стикерпак '{pack_title}' из локального кэша на диске и из списка?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._remove_pack_by_name(pack_name, from_cache=True)

    def _remove_current_pack(self):
        row = self.pack_list_widget.currentRow()
        if row < 0:
            return
        item = self.pack_list_widget.item(row)
        pack_name = item.data(Qt.UserRole)
        if pack_name:
            self._remove_pack_by_name(pack_name, from_cache=False)

    def _remove_pack_by_name(self, pack_name: str, from_cache: bool = False):
        pack_data = next((p for p in self.packs if p.name == pack_name), None)

        if from_cache and pack_data:
            delete_pack_from_cache(pack_name, pack_data.stickers)
            self.status_label.setText(f"Пак '{pack_data.title}' удален из кэша.")
        elif from_cache:
            delete_pack_from_cache(pack_name)

        # Remove from tabs dict & stacked widget
        tab = self.pack_tabs.pop(pack_name, None)
        if tab:
            self.content_stack.removeWidget(tab)
            tab.deleteLater()

        list_item = self.pack_list_items.pop(pack_name, None)
        if list_item:
            row = self.pack_list_widget.row(list_item)
            if row >= 0:
                self.pack_list_widget.takeItem(row)

        # Remove from self.packs list
        self.packs = [p for p in self.packs if p.name != pack_name]

        if self.pack_list_widget.count() == 0:
            self.content_stack.setCurrentWidget(self.placeholder_widget)
            self.btn_remove_pack.setEnabled(False)

        self._on_selection_updated()

    def _on_mode_tab_changed(self, index: int):
        if not hasattr(self, "bottom_frame"):
            return
        if index == 0:
            self.bottom_frame.show()
        elif index == 1:
            # Switched to Selected Stickers workspace
            self.bottom_frame.show()
            selected_items = self._get_all_selected_items_with_packs()
            self.selected_stickers_view.refresh_stickers(selected_items)
        elif index == 2:
            # Switched to Owned Packs Editor
            self.bottom_frame.hide()
            self.pack_editor_view.refresh_pack_list()

    def _get_all_selected_items_flat(self) -> List[StickerItem]:
        if hasattr(self, "selected_stickers_view") and self.selected_stickers_view.selected_items_with_packs:
            ordered = [s for s in self.selected_stickers_view.get_ordered_stickers() if s.is_selected]
            if ordered:
                existing_fids = {s.file_id for s in ordered}
                for pack in self.packs:
                    tab = self.pack_tabs.get(pack.name)
                    stickers = tab.get_selected_stickers() if tab else [s for s in pack.stickers if s.is_selected]
                    for s in stickers:
                        if s.file_id not in existing_fids:
                            ordered.append(s)
                            existing_fids.add(s.file_id)
                return ordered

        selected_map: Dict[str, StickerItem] = {}
        for pack in self.packs:
            tab = self.pack_tabs.get(pack.name)
            stickers = tab.get_selected_stickers() if tab else [s for s in pack.stickers if s.is_selected]
            for s in stickers:
                selected_map[s.file_id] = s

        # Restore custom order if saved
        order = load_selected_order()
        ordered_res: List[StickerItem] = []
        for fid in order:
            if fid in selected_map:
                ordered_res.append(selected_map.pop(fid))
        ordered_res.extend(selected_map.values())
        return ordered_res

    def _get_all_selected_items_with_packs(self) -> List[tuple[StickerItem, str, str]]:
        # Returns list of (StickerItem, pack_title, pack_format)
        selected_map: Dict[str, tuple[StickerItem, str, str]] = {}
        for pack in self.packs:
            tab = self.pack_tabs.get(pack.name)
            pack_title = pack.title
            pack_format = pack.format_type
            stickers = tab.get_selected_stickers() if tab else [s for s in pack.stickers if s.is_selected]
            for s in stickers:
                selected_map[s.file_id] = (s, pack_title, pack_format)

        # Restore custom user order
        order = load_selected_order()
        ordered_res: List[tuple[StickerItem, str, str]] = []
        for fid in order:
            if fid in selected_map:
                ordered_res.append(selected_map.pop(fid))
        ordered_res.extend(selected_map.values())
        return ordered_res

    def _on_selected_view_updated(self):
        # Refresh pack tab card styles when deselected or changed in SelectedStickersView
        for tab in self.pack_tabs.values():
            for card in tab.cards:
                card._update_ui_state()
            tab._update_counter()
        
        # Persist selection order directly from user-customized order
        ordered_stickers = self.selected_stickers_view.get_ordered_stickers()
        save_selected_order([s.file_id for s in ordered_stickers])
        
        self._on_selection_updated()

    # ----------------------------------------------------
    # Selection & Validation Logic
    # ----------------------------------------------------
    def _on_selection_updated(self):
        static_count = 0
        animated_count = 0
        video_count = 0

        for pack in self.packs:
            tab = self.pack_tabs.get(pack.name)
            selected = tab.get_selected_stickers() if tab else [s for s in pack.stickers if s.is_selected]
            for s in selected:
                fmt = s.get_effective_format(pack.format_type).lower()
                if fmt == "static":
                    static_count += 1
                elif fmt == "animated":
                    animated_count += 1
                elif fmt == "video":
                    video_count += 1

        total_selected = static_count + animated_count + video_count
        self.summary_label.setText(
            f"Выбрано стикеров: <b>{total_selected}</b> "
            f"(Статика: {static_count} | Анимация: {animated_count} | Видео: {video_count})"
        )
        self.mode_tabs.setTabText(1, f"🎨 Выбранные стикеры ({total_selected})")

        self._validate_export_inputs()

    def _on_format_changed(self):
        self._validate_export_inputs()

    def _validate_export_inputs(self):
        target_format = self.format_combo.currentData()

        # Count selected stickers for target format vs incompatible
        compatible_stickers: List[StickerItem] = []
        incompatible_count = 0

        for pack in self.packs:
            tab = self.pack_tabs.get(pack.name)
            selected = tab.get_selected_stickers() if tab else [s for s in pack.stickers if s.is_selected]
            for s in selected:
                fmt = s.get_effective_format(pack.format_type).lower()
                if fmt == target_format:
                    compatible_stickers.append(s)
                else:
                    incompatible_count += 1

        # Warnings & Validation
        has_error = False
        warning_msg = ""

        if incompatible_count > 0:
            warning_msg = (
                f"⚠️ Внимание: выбрано {incompatible_count} стикеров другого формата. "
                f"Telegram запрещает смешивать форматы. В пак войдут только {len(compatible_stickers)} стикеров выбранного формата ({target_format})."
            )
            self.warning_label.setText(warning_msg)
            self.warning_label.show()
        else:
            self.warning_label.hide()

        title = self.title_input.text().strip()
        short_name = self.name_input.text().strip()
        is_configured = self.config_manager.is_configured()

        can_create = (
            len(compatible_stickers) > 0
            and bool(title)
            and bool(short_name)
            and is_configured
            and self.create_worker is None
        )

        self.btn_create_pack.setEnabled(can_create)

    def _update_ui_state(self):
        self._on_selection_updated()

    # ----------------------------------------------------
    # Export / Creation
    # ----------------------------------------------------
    def _start_creating_pack(self):
        if not self.config_manager.is_configured():
            QMessageBox.warning(
                self,
                "Требуется настройка",
                "Пожалуйста, заполните токен бота и User ID в окне настроек ⚙."
            )
            self._open_settings()
            return

        target_format = self.format_combo.currentData()
        title = self.title_input.text().strip()
        short_name = self.name_input.text().strip()
        bot_username = self.config_manager.bot_username

        if not short_name:
            QMessageBox.warning(self, "Ошибка", "Укажите short_name стикерпака.")
            return

        # Full name must end with _by_<bot_username> for Telegram API
        full_name = f"{short_name}_by_{bot_username}"

        # Collect compatible stickers in user defined order
        all_ordered = self._get_all_selected_items_flat()
        stickers_to_export: List[StickerItem] = []
        
        # Build pack format lookup
        pack_format_map = {p.name: p.format_type for p in self.packs}
        
        for s in all_ordered:
            # Check effective format
            eff_fmt = s.format_override
            if not eff_fmt:
                # find parent pack
                for p in self.packs:
                    if any(st.file_id == s.file_id for st in p.stickers):
                        eff_fmt = p.format_type
                        break
            if (eff_fmt or "static").lower() == target_format:
                stickers_to_export.append(s)

        if not stickers_to_export:
            QMessageBox.warning(
                self,
                "Нет стикеров",
                f"Не выбрано ни одного стикера формата '{target_format}' для экспорта."
            )
            return

        # Confirm creation (do NOT show _by_<bot_username> in the user dialog)
        confirm = QMessageBox.question(
            self,
            "Подтверждение",
            f"Создать стикерпак '{title}' ({short_name}) из {len(stickers_to_export)} стикеров?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        self.btn_create_pack.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.status_label.setText("Создание стикерпака в Telegram...")

        self.create_worker = CreatePackWorker(
            bot_token=self.config_manager.bot_token,
            user_id=self.config_manager.user_id,
            name=full_name,
            title=title,
            sticker_format=target_format,
            stickers=stickers_to_export,
            parent=self
        )
        self.create_worker.progress.connect(self._on_create_progress)
        self.create_worker.success.connect(self._on_create_success)
        self.create_worker.error.connect(self._on_create_error)
        self.create_worker.start()

    def _on_create_progress(self, percent: int, message: str):
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)

    def _on_create_success(self, pack_link: str):
        self.progress_bar.hide()
        self.status_label.setText(f"Стикерпак успешно создан: {pack_link}")
        self.create_worker = None
        self._validate_export_inputs()

        # Show success dialog with copy button
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Успех! 🎉")
        msg_box.setText(
            f"<h3>Стикерпак успешно создан!</h3>"
            f"<p>Ссылка на ваш новый стикерпак:</p>"
            f"<p><a href='{pack_link}'>{pack_link}</a></p>"
        )
        btn_copy = msg_box.addButton("📋 Скопировать ссылку", QMessageBox.ActionRole)
        btn_ok = msg_box.addButton("Отлично", QMessageBox.AcceptRole)
        msg_box.exec()

        if msg_box.clickedButton() == btn_copy:
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(pack_link)
            self.status_label.setText(f"Ссылка скопирована в буфер: {pack_link}")

    def _on_create_error(self, error_msg: str):
        self.progress_bar.hide()
        self.status_label.setText(f"Ошибка: {error_msg}")
        self.create_worker = None
        self._validate_export_inputs()
        QMessageBox.critical(self, "Ошибка создания стикерпака", error_msg)

    # ----------------------------------------------------
    # MTProto Pack Creation (no _by_bot suffix)
    # ----------------------------------------------------
    def _start_creating_pack_mtproto(self):
        from core.mtproto_client import is_session_authorized

        cfg = self.config_manager
        if not cfg.is_mtproto_configured():
            QMessageBox.warning(
                self,
                "Требуется авторизация",
                "Войдите в аккаунт Telegram через MTProto.\nОткрываю диалог авторизации..."
            )
            self._open_mtproto_auth()
            return

        # Check session is still valid
        authorized = is_session_authorized(cfg.api_id, cfg.api_hash, cfg.session_name)
        if not authorized:
            reply = QMessageBox.question(
                self,
                "Сессия не активна",
                "Сессия MTProto не авторизована. Войти в аккаунт?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self._open_mtproto_auth()
            return

        target_format = self.format_combo.currentData()
        title = self.title_input.text().strip()
        short_name = self.name_input.text().strip()

        if not title or not short_name:
            QMessageBox.warning(self, "Ошибка", "Укажите название и short_name стикерпака.")
            return

        # Collect compatible stickers
        all_ordered = self._get_all_selected_items_flat()
        stickers_to_export = []
        for s in all_ordered:
            eff_fmt = s.format_override
            if not eff_fmt:
                for p in self.packs:
                    if any(st.file_id == s.file_id for st in p.stickers):
                        eff_fmt = p.format_type
                        break
            if (eff_fmt or "static").lower() == target_format:
                stickers_to_export.append(s)

        if not stickers_to_export:
            QMessageBox.warning(
                self,
                "Нет стикеров",
                f"Не выбрано ни одного стикера формата '{target_format}'.",
            )
            return

        confirm = QMessageBox.question(
            self,
            "Подтверждение",
            f"Создать стикерпак '<b>{title}</b>' (<code>{short_name}</code>) "
            f"из {len(stickers_to_export)} стикеров от имени вашего аккаунта?\n\n"
            f"Ссылка будет: t.me/addstickers/{short_name}",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        self.btn_create_pack.setEnabled(False)
        self.btn_create_mtproto.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.status_label.setText("Создание стикерпака через MTProto...")

        self.create_worker = CreatePackMTProtoWorker(
            api_id=cfg.api_id,
            api_hash=cfg.api_hash,
            session_name=cfg.session_name,
            bot_token=cfg.bot_token,
            short_name=short_name,
            title=title,
            sticker_format=target_format,
            stickers=stickers_to_export,
            parent=self,
        )
        self.create_worker.progress.connect(self._on_create_progress)
        self.create_worker.success.connect(self._on_create_success)
        self.create_worker.error.connect(self._on_create_error)
        self.create_worker.start()

    def _open_mtproto_auth(self):
        from ui.mtproto_auth_dialog import MTProtoAuthDialog
        dialog = MTProtoAuthDialog(self.config_manager, self)
        dialog.exec()

    def _create_tab_for_pack(self, pack_data: StickerPackData, create_widget: bool = True):
        fmt_icon = "🖼️"
        if pack_data.format_type == "animated":
            fmt_icon = "✨"
        elif pack_data.format_type == "video":
            fmt_icon = "🎥"

        # Sidebar Item with clean horizontal title and count
        item_text = f"{fmt_icon}  {pack_data.title}  ({len(pack_data.stickers)})"
        list_item = QListWidgetItem(item_text)
        list_item.setData(Qt.UserRole, pack_data.name)
        list_item.setToolTip(f"{pack_data.title} ({pack_data.format_type}) — {len(pack_data.stickers)} стикеров\nИмя: {pack_data.name}")
        list_item.setSizeHint(QSize(200, 42))

        self.pack_list_items[pack_data.name] = list_item
        self.pack_list_widget.addItem(list_item)
        self.btn_remove_pack.setEnabled(True)

        if create_widget:
            tab = self._get_or_create_pack_tab(pack_data.name)
            self.pack_list_widget.setCurrentItem(list_item)
            if tab:
                self.content_stack.setCurrentWidget(tab)
            self._on_selection_updated()

    def _load_cached_packs(self):
        """Быстрая загрузка уже скачанных стикерпаков из кэша при старте (Lazy Loading).
        В боковое меню добавляются элементы сразу, а тяжелые карточки стикеров создаются
        только при клике по конкретному паку.
        """
        cached = load_all_packs()
        if cached:
            self.packs.extend(cached)
            for p in cached:
                self._create_tab_for_pack(p, create_widget=False)
            
            # Select and render only the first pack on startup
            if self.pack_list_widget.count() > 0:
                first_item = self.pack_list_widget.item(0)
                self.pack_list_widget.setCurrentItem(first_item)
                first_pack_name = first_item.data(Qt.UserRole)
                first_tab = self._get_or_create_pack_tab(first_pack_name)
                if first_tab:
                    self.content_stack.setCurrentWidget(first_tab)

            self.status_label.setText(f"Загружено {len(cached)} паков из кэша")
            self._on_selection_updated()

    def closeEvent(self, event):
        # Persist current selection state and order for all loaded packs before exit
        for pack in self.packs:
            save_pack(pack)
        if hasattr(self, "selected_stickers_view") and self.selected_stickers_view.selected_items_with_packs:
            save_selected_order([s.file_id for s in self.selected_stickers_view.get_ordered_stickers()])
        super().closeEvent(event)



