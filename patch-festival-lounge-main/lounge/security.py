from __future__ import annotations

import hashlib
import hmac
import itertools
import re
import secrets
import unicodedata

from cryptography.fernet import Fernet, InvalidToken

PHONE_PATTERN = re.compile(r"\D+")
DISPLAY_CODE_PATTERN = re.compile(r"^[A-Z]{2,4}$")
DISPLAY_CODE_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "")
    return " ".join(normalized.strip().split())


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


def identity_digest(name: str, normalized_phone: str, secret: str) -> str:
    payload = f"{normalize_name(name)}\0{phone_digest(normalized_phone)}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def identity_digest_from_phone_hash(name: str, stored_phone_hash: str, secret: str) -> str:
    payload = f"{normalize_name(name)}\0{stored_phone_hash}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


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
    for length in (2, 3, 4):
        capacity = len(DISPLAY_CODE_ALPHABET) ** length
        used_at_length = {value for value in used if len(value) == length}
        if len(used_at_length) >= capacity:
            continue

        if length <= 3:
            available = [
                "".join(chars)
                for chars in itertools.product(DISPLAY_CODE_ALPHABET, repeat=length)
                if "".join(chars) not in used_at_length
            ]
            return secrets.choice(available)

        for _attempt in range(1000):
            candidate = "".join(secrets.choice(DISPLAY_CODE_ALPHABET) for _ in range(length))
            if candidate not in used_at_length:
                return candidate
        for chars in itertools.product(DISPLAY_CODE_ALPHABET, repeat=length):
            candidate = "".join(chars)
            if candidate not in used_at_length:
                return candidate

    raise ValueError("사용 가능한 참가자 ID가 없습니다.")


def new_internal_record_key(excluded: set[str] | None = None) -> str:
    used = excluded or set()
    while True:
        candidate = "~" + secrets.token_hex(3)
        if candidate not in used:
            return candidate
