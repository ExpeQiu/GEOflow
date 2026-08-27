"""AI API Key 加解密 — enc:v1 AES-GCM（对齐 Laravel ApiKeyCrypto）。"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import get_settings

ENC_PREFIX = "enc:v1:"


def _derive_key(app_key: str) -> bytes:
    key = app_key
    if key.startswith("base64:"):
        key = base64.b64decode(key[7:]).decode("latin-1")
    return hashlib.sha256(key.encode()).digest()[:32]


def encrypt_api_key(plaintext: str, app_key: str | None = None) -> str:
    """明文 → enc:v1:...；已加密或空串原样返回。"""
    raw = (plaintext or "").strip()
    if not raw or raw.startswith(ENC_PREFIX):
        return raw
    material = (app_key or get_settings().encryption_key_material()).strip()
    iv = os.urandom(12)
    aes = AESGCM(_derive_key(material))
    sealed = aes.encrypt(iv, raw.encode("utf-8"), None)
    ct, tag = sealed[:-16], sealed[-16:]
    payload = {
        "iv": base64.b64encode(iv).decode(),
        "value": base64.b64encode(ct).decode(),
        "tag": base64.b64encode(tag).decode(),
    }
    blob = base64.b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()
    return f"{ENC_PREFIX}{blob}"


def decrypt_api_key(ciphertext: str, app_key: str | None = None) -> str:
    """解密 enc:v1:...；非加密格式原样返回（兼容历史明文）。"""
    if not ciphertext or not ciphertext.startswith(ENC_PREFIX):
        return ciphertext
    material = (app_key or get_settings().encryption_key_material()).strip()
    payload_b64 = ciphertext[len(ENC_PREFIX) :]
    raw = base64.b64decode(payload_b64)
    data = json.loads(raw.decode("utf-8"))
    iv = base64.b64decode(data["iv"])
    tag = base64.b64decode(data["tag"])
    ct = base64.b64decode(data["value"])
    aes = AESGCM(_derive_key(material))
    plain = aes.decrypt(iv, ct + tag, None)
    return plain.decode("utf-8")


def looks_encrypted(value: str) -> bool:
    return bool(value) and value.startswith(ENC_PREFIX)
