"""
Dialog for authenticating a Telegram user account via Telethon (MTProto).
Handles phone → code → optional 2FA password flow.
"""
import asyncio
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QStackedWidget,
    QWidget,
)

from core.config_manager import ConfigManager


SESSION_DIR = Path(".sessions")


class _AuthWorker(QThread):
    """Background thread running async Telethon auth steps."""

    code_requested = Signal()           # server sent a code
    password_requested = Signal()       # 2FA password needed
    success = Signal()
    error = Signal(str)

    def __init__(self, api_id: int, api_hash: str, session_name: str, phone: str):
        super().__init__()
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.phone = phone
        self._code: str = ""
        self._password: str = ""
        self._client = None
        self._phone_code_hash: str = ""

    # Called from GUI thread after user enters code
    def provide_code(self, code: str):
        self._code = code

    def provide_password(self, pw: str):
        self._password = pw

    def run(self):
        asyncio.run(self._auth_flow())

    async def _auth_flow(self):
        from telethon import TelegramClient
        from telethon.errors import SessionPasswordNeededError

        SESSION_DIR.mkdir(exist_ok=True)
        session_path = str(SESSION_DIR / self.session_name)

        try:
            client = TelegramClient(session_path, self.api_id, self.api_hash)
            await client.connect()
            self._client = client

            if await client.is_user_authorized():
                self.success.emit()
                await client.disconnect()
                return

            result = await client.send_code_request(self.phone)
            self._phone_code_hash = result.phone_code_hash
            self.code_requested.emit()

            # Wait until GUI provides the code (poll with sleep)
            for _ in range(600):   # up to 60 seconds
                await asyncio.sleep(0.1)
                if self._code:
                    break

            if not self._code:
                self.error.emit("Код подтверждения не был введён вовремя.")
                await client.disconnect()
                return

            try:
                await client.sign_in(self.phone, self._code, phone_code_hash=self._phone_code_hash)
            except SessionPasswordNeededError:
                self.password_requested.emit()
                for _ in range(600):
                    await asyncio.sleep(0.1)
                    if self._password:
                        break
                if not self._password:
                    self.error.emit("Пароль двухфакторной аутентификации не был введён.")
                    await client.disconnect()
                    return
                await client.sign_in(password=self._password)

            self.success.emit()
            await client.disconnect()

        except Exception as e:
            self.error.emit(str(e))


class MTProtoAuthDialog(QDialog):
    """Step-by-step MTProto login dialog (phone → code → optional 2FA)."""

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self._worker: _AuthWorker | None = None
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("Вход в аккаунт Telegram (MTProto)")
        self.setMinimumWidth(440)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)

        self.stack = QStackedWidget(self)

        # --- Page 0: credentials + phone ---
        page_phone = QWidget()
        lay0 = QVBoxLayout(page_phone)
        lay0.setSpacing(8)

        _lbl_style = "color: #cdd6f4; font-size: 12px; font-weight: 600;"

        lbl_api_id = QLabel("API ID", page_phone)
        lbl_api_id.setStyleSheet(_lbl_style)
        lay0.addWidget(lbl_api_id)
        self.api_id_input = QLineEdit(page_phone)
        self.api_id_input.setPlaceholderText("2040")
        if self.config_manager.api_id:
            self.api_id_input.setText(str(self.config_manager.api_id))
        lay0.addWidget(self.api_id_input)

        lbl_api_hash = QLabel("API Hash", page_phone)
        lbl_api_hash.setStyleSheet(_lbl_style)
        lay0.addWidget(lbl_api_hash)
        self.api_hash_input = QLineEdit(page_phone)
        self.api_hash_input.setPlaceholderText("b18441a1ff607e10a989891a5462e627")
        self.api_hash_input.setText(self.config_manager.api_hash)
        lay0.addWidget(self.api_hash_input)

        lbl_phone = QLabel("Номер телефона (+ код страны)", page_phone)
        lbl_phone.setStyleSheet(_lbl_style)
        lay0.addWidget(lbl_phone)
        self.phone_input = QLineEdit(page_phone)
        self.phone_input.setPlaceholderText("+79001234567")
        self.phone_input.setText(self.config_manager.phone_number)
        lay0.addWidget(self.phone_input)

        self.btn_send_code = QPushButton("Получить код →", page_phone)
        self.btn_send_code.setObjectName("PrimaryButton")
        self.btn_send_code.clicked.connect(self._start_auth)
        lay0.addWidget(self.btn_send_code)

        self.stack.addWidget(page_phone)

        # --- Page 1: enter code ---
        page_code = QWidget()
        lay1 = QVBoxLayout(page_code)
        lay1.setSpacing(8)
        lbl_code_info = QLabel(
            "Введите код, который пришёл в ваш Telegram.\n"
            "(Проверьте сообщения в приложении Telegram.)",
            page_code,
        )
        lbl_code_info.setWordWrap(True)
        lbl_code_info.setStyleSheet("color: #a6adc8;")
        lay1.addWidget(lbl_code_info)
        lbl_code = QLabel("Код подтверждения", page_code)
        lbl_code.setStyleSheet("color: #cdd6f4; font-size: 12px; font-weight: 600;")
        lay1.addWidget(lbl_code)
        self.code_input = QLineEdit(page_code)
        self.code_input.setPlaceholderText("12345")
        lay1.addWidget(self.code_input)
        self.btn_submit_code = QPushButton("Подтвердить →", page_code)
        self.btn_submit_code.setObjectName("PrimaryButton")
        self.btn_submit_code.clicked.connect(self._submit_code)
        lay1.addWidget(self.btn_submit_code)
        self.stack.addWidget(page_code)

        # --- Page 2: 2FA password ---
        page_pw = QWidget()
        lay2 = QVBoxLayout(page_pw)
        lay2.setSpacing(8)
        lbl_pw = QLabel("Требуется облачный пароль (2FA):", page_pw)
        lbl_pw.setStyleSheet("color: #cdd6f4; font-size: 12px; font-weight: 600;")
        lay2.addWidget(lbl_pw)
        self.pw_input = QLineEdit(page_pw)
        self.pw_input.setEchoMode(QLineEdit.Password)
        self.pw_input.setPlaceholderText("Пароль...")
        lay2.addWidget(self.pw_input)
        self.btn_submit_pw = QPushButton("Войти →", page_pw)
        self.btn_submit_pw.setObjectName("PrimaryButton")
        self.btn_submit_pw.clicked.connect(self._submit_password)
        lay2.addWidget(self.btn_submit_pw)
        self.stack.addWidget(page_pw)

        root.addWidget(self.stack)

        self.status_label = QLabel("", self)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #89b4fa; font-size: 12px;")
        root.addWidget(self.status_label)

        root.addStretch()

        bottom = QHBoxLayout()
        bottom.addStretch()
        btn_cancel = QPushButton("Отмена", self)
        btn_cancel.clicked.connect(self.reject)
        bottom.addWidget(btn_cancel)
        root.addLayout(bottom)

    # ------------------------------------------------------------------

    def _start_auth(self):
        api_id_str = self.api_id_input.text().strip()
        api_hash = self.api_hash_input.text().strip()
        phone = self.phone_input.text().strip()

        if not api_id_str.isdigit() or not api_hash or not phone:
            self.status_label.setStyleSheet("color: #f38ba8;")
            self.status_label.setText("Заполните все поля.")
            return

        api_id = int(api_id_str)
        self.config_manager.save_mtproto(
            api_id=api_id,
            api_hash=api_hash,
            phone_number=phone,
            session_name=self.config_manager.session_name or "tgstickers",
        )

        self.btn_send_code.setEnabled(False)
        self.status_label.setStyleSheet("color: #89b4fa;")
        self.status_label.setText("Отправка запроса кода...")

        self._worker = _AuthWorker(api_id, api_hash, self.config_manager.session_name, phone)
        self._worker.code_requested.connect(self._on_code_requested)
        self._worker.password_requested.connect(self._on_password_requested)
        self._worker.success.connect(self._on_success)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_code_requested(self):
        self.status_label.setText("Код отправлен. Введите его ниже.")
        self.stack.setCurrentIndex(1)

    def _submit_code(self):
        code = self.code_input.text().strip()
        if not code:
            return
        self.btn_submit_code.setEnabled(False)
        self.status_label.setText("Проверка кода...")
        if self._worker:
            self._worker.provide_code(code)

    def _on_password_requested(self):
        self.status_label.setText("Требуется пароль 2FA.")
        self.stack.setCurrentIndex(2)

    def _submit_password(self):
        pw = self.pw_input.text()
        if not pw:
            return
        self.btn_submit_pw.setEnabled(False)
        self.status_label.setText("Проверка пароля...")
        if self._worker:
            self._worker.provide_password(pw)

    def _on_success(self):
        self.status_label.setStyleSheet("color: #a6e3a1;")
        self.status_label.setText("Авторизация успешна!")
        QMessageBox.information(self, "Успех", "Вы успешно вошли в аккаунт Telegram!")
        self.accept()

    def _on_error(self, msg: str):
        self.status_label.setStyleSheet("color: #f38ba8;")
        self.status_label.setText(f"Ошибка: {msg}")
        self.btn_send_code.setEnabled(True)
        self.btn_submit_code.setEnabled(True)
        self.btn_submit_pw.setEnabled(True)
