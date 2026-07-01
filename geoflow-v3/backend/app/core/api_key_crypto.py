"""Laravel APP_KEY 解密 — 数据迁移时解密 ai_models.api_key。"""

import base64
import hashlib
import json
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def decrypt_api_key(ciphertext: str, app_key: str) -> str:
    """解密 enc:v1:... 格式 API Key（对齐 Laravel ApiKeyCrypto）。"""
    if not ciphertext.startswith("enc:v1:"):
        return ciphertext
    payload_b64 = ciphertext[len("enc:v1:") :]
    raw = base64.b64decode(payload_b64)
    data = json.loads(raw.decode("utf-8"))
    iv = base64.b64decode(data["iv"])
    tag = base64.b64decode(data["tag"])
    ct = base64.b64decode(data["value"])
    key_material = _derive_key(app_key)
    aes = AESGCM(key_material)
    plain = aes.decrypt(iv, ct + tag, None)
    return plain.decode("utf-8")


def _derive_key(app_key: str) -> bytes:
    key = app_key
    if key.startswith("base64:"):
        key = base64.b64decode(key[7:]).decode("latin-1")
    return hashlib.sha256(key.encode()).digest()[:32]
