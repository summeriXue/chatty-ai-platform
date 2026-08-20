"""WeCom callback cryptography helpers."""

import base64
import hashlib
import struct

from Crypto.Cipher import AES


def verify_signature(
    token: str,
    timestamp: str,
    nonce: str,
    encrypted: str,
    msg_signature: str,
) -> bool:
    """Verify WeCom callback SHA1 signature."""
    values = [
        token,
        timestamp,
        nonce,
        encrypted,
    ]
    values.sort()

    raw = "".join(values).encode("utf-8")
    expected = hashlib.sha1(raw).hexdigest()

    return expected == msg_signature


def decrypt_message(
    encoding_aes_key: str,
    encrypted: str,
    receive_id: str,
) -> str:
    """Decrypt a WeCom encrypted callback payload."""

    aes_key = base64.b64decode(
        encoding_aes_key + "="
    )

    cipher = AES.new(
        aes_key,
        AES.MODE_CBC,
        iv=aes_key[:16],
    )

    encrypted_bytes = base64.b64decode(encrypted)
    decrypted = cipher.decrypt(encrypted_bytes)

    # PKCS#7 unpadding
    pad = decrypted[-1]
    if pad < 1 or pad > 32:
        raise ValueError("Invalid WeCom AES padding")

    decrypted = decrypted[:-pad]

    # WeCom plaintext format:
    # 16 random bytes + 4-byte msg length + message + receive_id
    content = decrypted[16:]

    msg_len = struct.unpack(
        "!I",
        content[:4],
    )[0]

    message = content[4:4 + msg_len]
    actual_receive_id = content[4 + msg_len:].decode("utf-8")

    if actual_receive_id != receive_id:
        raise ValueError(
            "WeCom receive_id mismatch"
        )

    return message.decode("utf-8")
