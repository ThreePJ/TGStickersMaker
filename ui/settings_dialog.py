from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
)

from core.config_manager import ConfigManager
from utils.workers import ValidateTokenWorker


class SettingsDialog(QDialog):
    """Settings dialog for configuring Bot Token and User ID."""

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.worker: ValidateTokenWorker = None
        self._init_ui()
        self._load_current_values()

    def _init_ui(self):
        self.setWindowTitle("Настройки")
        self.setFixedSize(500, 340)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # Description
        info_label = QLabel(self)
        info_label.setTextFormat(Qt.RichText)
        info_label.setText(
            "Для работы требуется Telegram Bot Token и ваш User ID.<br>"
            "Токен можно получить у <b>@BotFather</b>, а ID — у <b>@userinfobot</b>."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #a6adc8; font-size: 12px; padding-bottom: 4px;")
        layout.addWidget(info_label)

        # Bot Token
        token_label = QLabel("Bot Token", self)
        token_label.setStyleSheet("color: #6c7086; font-size: 11px; font-weight: 600;")
        layout.addWidget(token_label)

        token_input_layout = QHBoxLayout()
        token_input_layout.setSpacing(6)
        self.token_input = QLineEdit(self)
        self.token_input.setPlaceholderText("1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
        self.token_input.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        token_input_layout.addWidget(self.token_input)

        self.btn_toggle_token = QPushButton("👁", self)
        self.btn_toggle_token.setObjectName("SettingsButton")
        self.btn_toggle_token.setFixedSize(40, 36)
        self.btn_toggle_token.setToolTip("Показать/скрыть токен")
        self.btn_toggle_token.clicked.connect(self._toggle_token_visibility)
        token_input_layout.addWidget(self.btn_toggle_token)
        layout.addLayout(token_input_layout)

        # Telegram User ID
        user_id_label = QLabel("User ID (числовой)", self)
        user_id_label.setStyleSheet("color: #6c7086; font-size: 11px; font-weight: 600;")
        layout.addWidget(user_id_label)

        self.user_id_input = QLineEdit(self)
        self.user_id_input.setPlaceholderText("123456789")
        self.user_id_input.setValidator(QIntValidator(1, 2147483647, self))
        layout.addWidget(self.user_id_input)

        # Bot Username (Display)
        bot_user_layout = QHBoxLayout()
        bot_user_title = QLabel("Бот:", self)
        bot_user_title.setStyleSheet("color: #6c7086; font-size: 12px;")
        self.bot_user_label = QLabel("—", self)
        self.bot_user_label.setStyleSheet("color: #89b4fa; font-weight: bold; font-size: 12px;")
        bot_user_layout.addWidget(bot_user_title)
        bot_user_layout.addWidget(self.bot_user_label)
        bot_user_layout.addStretch()
        layout.addLayout(bot_user_layout)

        # Status Message
        self.status_label = QLabel("", self)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        buttons_layout.addStretch()

        self.btn_cancel = QPushButton("Отмена", self)
        self.btn_cancel.setFixedHeight(34)
        self.btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Проверить и сохранить", self)
        self.btn_save.setObjectName("PrimaryButton")
        self.btn_save.setFixedHeight(34)
        self.btn_save.clicked.connect(self._on_save_clicked)
        buttons_layout.addWidget(self.btn_save)

        layout.addLayout(buttons_layout)

    def _toggle_token_visibility(self):
        if self.token_input.echoMode() == QLineEdit.Password:
            self.token_input.setEchoMode(QLineEdit.Normal)
        else:
            self.token_input.setEchoMode(QLineEdit.Password)

    def _load_current_values(self):
        self.token_input.setText(self.config_manager.bot_token)
        if self.config_manager.user_id:
            self.user_id_input.setText(str(self.config_manager.user_id))
        if self.config_manager.bot_username:
            self.bot_user_label.setText(f"@{self.config_manager.bot_username}")

    def _on_save_clicked(self):
        token = self.token_input.text().strip()
        user_id_str = self.user_id_input.text().strip()

        if not token:
            self.status_label.setStyleSheet("color: #f38ba8;")
            self.status_label.setText("Пожалуйста, введите токен бота.")
            return

        if not user_id_str or not user_id_str.isdigit():
            self.status_label.setStyleSheet("color: #f38ba8;")
            self.status_label.setText("Пожалуйста, укажите корректный числовой User ID.")
            return

        self.btn_save.setEnabled(False)
        self.status_label.setStyleSheet("color: #89b4fa;")
        self.status_label.setText("Проверка токена через Telegram Bot API...")

        self.worker = ValidateTokenWorker(token)
        self.worker.success.connect(lambda uname: self._on_validation_success(token, int(user_id_str), uname))
        self.worker.error.connect(self._on_validation_error)
        self.worker.start()

    def _on_validation_success(self, token: str, user_id: int, bot_username: str):
        self.btn_save.setEnabled(True)
        self.bot_user_label.setText(f"@{bot_username}")
        self.status_label.setStyleSheet("color: #a6e3a1;")
        self.status_label.setText("Токен успешно подтвержден!")

        self.config_manager.save(
            bot_token=token,
            user_id=user_id,
            bot_username=bot_username
        )
        QMessageBox.information(
            self,
            "Настройки сохранены",
            f"Конфигурация успешно сохранена!\nБот: @{bot_username}"
        )
        self.accept()

    def _on_validation_error(self, error_message: str):
        self.btn_save.setEnabled(True)
        self.status_label.setStyleSheet("color: #f38ba8;")
        self.status_label.setText(f"Ошибка проверки токена:\n{error_message}")
