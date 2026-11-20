"""Formato legado de senha (MD5 sem salt) e sua migração.

O código original gravava `md5(senha)` em hexadecimal. No boot esses valores são
envoltos em scrypt (`md5+scrypt:...`), sem precisar da senha original, e no
próximo login bem-sucedido viram scrypt puro.
"""
import hashlib
import re

from werkzeug.security import check_password_hash, generate_password_hash

LEGACY_PREFIX = 'md5+'
_LEGACY_MD5 = re.compile(r'[0-9a-f]{32}')


def is_raw_md5(stored):
    return bool(stored) and _LEGACY_MD5.fullmatch(stored) is not None


def md5_hex(raw_password):
    return hashlib.md5(raw_password.encode('utf-8')).hexdigest()


def wrap_md5(md5_value):
    return LEGACY_PREFIX + generate_password_hash(md5_value)


def is_wrapped(stored):
    return stored.startswith(LEGACY_PREFIX)


def check_wrapped(stored, raw_password):
    return check_password_hash(stored[len(LEGACY_PREFIX):], md5_hex(raw_password))
