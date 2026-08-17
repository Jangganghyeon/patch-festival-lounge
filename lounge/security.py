from __future__ import annotations

import hashlib
import re
import secrets

from cryptography.fernet import Fernet, InvalidToken

PHONE_PATTERN = re.compile(r"\D+")
DISPLAY_CODE_PATTERN = re.compile(r"^[A-Z]{2}$")
DISPLAY_CODE_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


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


def is_display_code(value: str) -> bool:
    return bool(DISPLAY_CODE_PATTERN.fullmatch(value or ""))


def new_display_code(excluded: set[str] | None = None) -> str:
    used = {value.upper() for value in (excluded or set())}
    available = [
        first + second
        for first in DISPLAY_CODE_ALPHABET
        for second in DISPLAY_CODE_ALPHABET
        if first + second not in used
    ]
    if not available:
        raise ValueError("사용 가능한 두 글자 참가자 ID 676개가 모두 배정되었습니다.")
    return secrets.choice(available)
