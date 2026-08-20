import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from dotenv import dotenv_values, set_key
except ImportError:
    dotenv_values = None
    set_key = None

ENV_FILE_PATH = Path(".env")
ENV_EXAMPLE_PATH = Path(".env.example")


class ConfigManager:
    """Manages reading and writing application configuration using standard .env format."""

    def __init__(self, env_path: Path = ENV_FILE_PATH):
        self.env_path = env_path
        self._config: Dict[str, Any] = self._load()

    def _parse_env_file(self, path: Path) -> Dict[str, str]:
        """Custom robust line parser in case python-dotenv is not yet installed."""
        values: Dict[str, str] = {}
        if not path.exists():
            return values
        try:
            with open(path, "r", encoding="utf-8") as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        values[key] = val
        except Exception:
            pass
        return values

    def _load(self) -> Dict[str, Any]:
        values: Dict[str, str] = {}

        if dotenv_values and self.env_path.exists():
            try:
                values = dict(dotenv_values(self.env_path))
            except Exception:
                values = self._parse_env_file(self.env_path)
        elif self.env_path.exists():
            values = self._parse_env_file(self.env_path)

        # Fallback to system environment variables if not found in .env
        bot_token = values.get("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN", "")
        bot_username = values.get("TELEGRAM_BOT_USERNAME") or os.getenv("TELEGRAM_BOT_USERNAME", "")
        raw_uid = values.get("TELEGRAM_USER_ID") or os.getenv("TELEGRAM_USER_ID", "")
        raw_owned = values.get("OWNED_PACKS") or os.getenv("OWNED_PACKS", "")

        # MTProto / User API fields
        raw_api_id = values.get("API_ID") or os.getenv("API_ID", "")
        api_hash = values.get("API_HASH") or os.getenv("API_HASH", "")
        phone_number = values.get("PHONE_NUMBER") or os.getenv("PHONE_NUMBER", "")
        session_name = values.get("SESSION_NAME") or os.getenv("SESSION_NAME", "tgstickers")

        user_id = None
        if raw_uid:
            try:
                user_id = int(raw_uid)
            except (ValueError, TypeError):
                user_id = None

        api_id = None
        if raw_api_id:
            try:
                api_id = int(raw_api_id)
            except (ValueError, TypeError):
                api_id = None

        owned_packs: List[str] = []
        if raw_owned:
            owned_packs = [p.strip() for p in raw_owned.split(",") if p.strip()]

        return {
            "bot_token": bot_token,
            "user_id": user_id,
            "bot_username": bot_username.lstrip("@"),
            "owned_packs": owned_packs,
            "api_id": api_id,
            "api_hash": api_hash,
            "phone_number": phone_number,
            "session_name": session_name,
        }

    def _write_env(self) -> None:
        """Writes current config values to .env file preserving clean structure."""
        token = self._config.get("bot_token", "")
        uid = self._config.get("user_id") or ""
        username = self._config.get("bot_username", "")
        owned_list = self._config.get("owned_packs", [])
        owned_str = ",".join(owned_list)

        api_id = self._config.get("api_id") or ""
        api_hash = self._config.get("api_hash", "")
        phone = self._config.get("phone_number", "")
        session = self._config.get("session_name", "tgstickers")

        content = (
            "# Telegram Bot Credentials\n"
            f"TELEGRAM_BOT_TOKEN={token}\n"
            f"TELEGRAM_USER_ID={uid}\n"
            f"TELEGRAM_BOT_USERNAME={username}\n\n"
            "# Comma-separated list of owned sticker pack short names\n"
            f"OWNED_PACKS={owned_str}\n\n"
            "# MTProto / User API credentials\n"
            f"API_ID={api_id}\n"
            f"API_HASH={api_hash}\n"
            f"PHONE_NUMBER={phone}\n"
            f"SESSION_NAME={session}\n"
        )
        try:
            with open(self.env_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"Error saving .env file: {e}")

    def save(self, bot_token: str, user_id: Optional[int], bot_username: str) -> None:
        owned = self._config.get("owned_packs", [])
        self._config = {
            "bot_token": bot_token.strip(),
            "user_id": int(user_id) if user_id is not None and str(user_id).isdigit() else user_id,
            "bot_username": bot_username.strip().lstrip("@"),
            "owned_packs": owned,
            "api_id": self._config.get("api_id"),
            "api_hash": self._config.get("api_hash", ""),
            "phone_number": self._config.get("phone_number", ""),
            "session_name": self._config.get("session_name", "tgstickers"),
        }
        self._write_env()

    def save_mtproto(self, api_id: int, api_hash: str, phone_number: str, session_name: str = "tgstickers") -> None:
        self._config["api_id"] = api_id
        self._config["api_hash"] = api_hash.strip()
        self._config["phone_number"] = phone_number.strip()
        self._config["session_name"] = session_name.strip() or "tgstickers"
        self._write_env()

    def add_owned_pack(self, pack_name: str) -> None:
        name = pack_name.strip()
        if not name:
            return
        packs = self._config.get("owned_packs", [])
        if name not in packs:
            packs.append(name)
            self._config["owned_packs"] = packs
            self._write_env()

    def remove_owned_pack(self, pack_name: str) -> None:
        name = pack_name.strip()
        packs = self._config.get("owned_packs", [])
        if name in packs:
            packs.remove(name)
            self._config["owned_packs"] = packs
            self._write_env()

    @property
    def owned_packs(self) -> list:
        return list(self._config.get("owned_packs", []))

    @property
    def bot_token(self) -> str:
        return self._config.get("bot_token", "")

    @property
    def user_id(self) -> Optional[int]:
        uid = self._config.get("user_id")
        if uid is not None:
            try:
                return int(uid)
            except (ValueError, TypeError):
                return None
        return None

    @property
    def bot_username(self) -> str:
        return self._config.get("bot_username", "")

    @property
    def api_id(self) -> Optional[int]:
        return self._config.get("api_id")

    @property
    def api_hash(self) -> str:
        return self._config.get("api_hash", "")

    @property
    def phone_number(self) -> str:
        return self._config.get("phone_number", "")

    @property
    def session_name(self) -> str:
        return self._config.get("session_name", "tgstickers")

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.user_id)

    def is_mtproto_configured(self) -> bool:
        return bool(self.api_id and self.api_hash and self.phone_number)
