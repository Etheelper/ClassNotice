import os
import hashlib
import base64

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

ENCRYPTION_KEY = hashlib.sha256(b'classnotice-encryption-key-2026').digest()


def _xor_encrypt(data_bytes, key):
    key_bytes = key
    result = bytearray()
    for i, b in enumerate(data_bytes):
        result.append(b ^ key_bytes[i % len(key_bytes)])
    return bytes(result)


def encrypt_data(data_str):
    if not data_str:
        return ''
    if HAS_CRYPTO:
        cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC)
        ct_bytes = cipher.encrypt(pad(data_str.encode('utf-8'), AES.block_size))
        iv = cipher.iv
        encrypted = base64.b64encode(iv + ct_bytes).decode('utf-8')
        return encrypted
    else:
        iv = os.urandom(16)
        data_bytes = data_str.encode('utf-8')
        combined = iv + _xor_encrypt(data_bytes, ENCRYPTION_KEY)
        return base64.b64encode(combined).decode('utf-8')


def decrypt_data(encrypted_str):
    if not encrypted_str:
        return ''
    try:
        raw = base64.b64decode(encrypted_str)
        if HAS_CRYPTO:
            iv = raw[:16]
            ct = raw[16:]
            cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC, iv)
            pt = unpad(cipher.decrypt(ct), AES.block_size)
            return pt.decode('utf-8')
        else:
            iv = raw[:16]
            ct = raw[16:]
            pt = _xor_encrypt(ct, ENCRYPTION_KEY)
            return pt.decode('utf-8')
    except Exception:
        return ''


def encrypt_config(config_dict):
    import json
    json_str = json.dumps(config_dict, ensure_ascii=False)
    return encrypt_data(json_str)


def decrypt_config(encrypted_str):
    import json
    json_str = decrypt_data(encrypted_str)
    if json_str:
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {}
    return {}
