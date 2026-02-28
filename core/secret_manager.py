"""API 키 암호화 저장/로드 관리자"""
import json
from pathlib import Path
from cryptography.fernet import Fernet

logger = None


def _log():
    global logger
    if logger is None:
        try:
            from core.logger import get_logger
            logger = get_logger(__name__)
        except Exception:
            import logging
            logger = logging.getLogger(__name__)
    return logger

SECRETS_DIR = Path(__file__).resolve().parent.parent / "data"
SECRETS_FILE = SECRETS_DIR / "secrets.enc"
KEY_FILE = SECRETS_DIR / ".secret_key"


def _get_or_create_key() -> bytes:
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()
    key = Fernet.generate_key()
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    KEY_FILE.write_bytes(key)
    return key


def save_secrets(secrets: dict) -> bool:
    try:
        SECRETS_DIR.mkdir(parents=True, exist_ok=True)
        fernet = Fernet(_get_or_create_key())
        data = json.dumps(secrets, ensure_ascii=False).encode("utf-8")
        encrypted = fernet.encrypt(data)
        SECRETS_FILE.write_bytes(encrypted)
        _log().info("secrets_saved", keys=list(secrets.keys()))
        return True
    except Exception as e:
        _log().error("secrets_save_failed", error=str(e))
        return False


def load_secrets() -> dict:
    try:
        if not SECRETS_FILE.exists():
            return {}
        fernet = Fernet(_get_or_create_key())
        encrypted = SECRETS_FILE.read_bytes()
        data = fernet.decrypt(encrypted)
        return json.loads(data.decode("utf-8"))
    except Exception as e:
        _log().error("secrets_load_failed", error=str(e))
        return {}


def get_secret(key: str, default: str = "") -> str:
    import os
    secrets = load_secrets()
    value = secrets.get(key, "")
    if value:
        return value
    return os.getenv(key, default)


def delete_secrets() -> bool:
    try:
        if SECRETS_FILE.exists():
            SECRETS_FILE.unlink()
        return True
    except Exception as e:
        _log().error("secrets_delete_failed", error=str(e))
        return False


def mask_key(key: str) -> str:
    if not key or len(key) < 10:
        return "미설정"
    return f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"
