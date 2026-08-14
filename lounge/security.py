from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets

from cryptography.fernet import Fernet, InvalidToken

PHONE_PATTERN = re.compile(r"\D+")


def normalize_phone(value: str) -> str:
    return PHONE_PATTERN.sub("", value or "")


def validate_phone(value: str) -> str:
    normalized = normalize_phone(value)
    if len(normalized) not in (10, 11):
        raise ValueError("전화번호는 숫자 10~11자리로 입력해 주세요.")
    if not normalized.startswith("0"):
        raise ValueError("국내 전화번호 형식으로 입력해 주세요.")
    return normalized


def mask_phone(value: str) -> str:
    normalized = normalize_phone(value)
    if len(normalized) == 11:
        return f"{normalized[:3]}-****-{normalized[-4:]}"
    if len(normalized) == 10:
        return f"{normalized[:3]}-***-{normalized[-4:]}"
    return "***-****-****"


def phone_digest(normalized_phone: str) -> str:
    return hashlib.sha256(normalized_phone.encode("utf-8")).hexdigest()


def encrypt_text(value: str, key: str) -> str:
    return Fernet(key.encode("ascii")).encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_text(value: str, key: str) -> str:
    try:
        return Fernet(key.encode("ascii")).decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise ValueError("저장된 개인정보를 복호화할 수 없습니다.") from exc


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("비밀번호는 8자 이상이어야 합니다.")
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return (
        "scrypt$16384$8$1$"
        + base64.urlsafe_b64encode(salt).decode()
        + "$"
        + base64.urlsafe_b64encode(derived).decode()
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_b64, digest_b64 = encoded.split("$")
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def new_display_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(6))
