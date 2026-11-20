"""Senhas de contas semeadas e migração de credenciais legadas no boot.

Nenhuma senha literal fica no código: as contas semeadas usam SEED_ADMIN_PASSWORD /
SEED_USER_PASSWORD, ou recebem uma senha aleatória exibida uma única vez no log.
"""
import logging
import secrets

from src.constants import ROLE_ADMIN
from src.database import db
from src.models import User
from src.models import legacy_password

logger = logging.getLogger(__name__)

# MD5 das senhas que o seed original publicava no repositório. Contas com esses
# hashes não podem manter a senha: recebem uma nova no boot.
KNOWN_DEFAULT_MD5 = frozenset({
    '81dc9bdb52d04dc20036dbd8313ed055',
    'e2fc714c4727ee9395f324cd2e7f331f',
    '1a1dc91c907325c69271ddf0c944bc72',
})


def seed_password(settings, role, email):
    """Senha para uma conta semeada: a do ambiente ou uma gerada e exibida uma vez."""
    if role == ROLE_ADMIN:
        configured, variable = settings.SEED_ADMIN_PASSWORD, 'SEED_ADMIN_PASSWORD'
    else:
        configured, variable = settings.SEED_USER_PASSWORD, 'SEED_USER_PASSWORD'
    if configured:
        logger.info('Senha de %s definida por %s', email, variable)
        return configured
    generated = secrets.token_urlsafe(12)
    logger.warning('Senha gerada para %s (exibida só agora): %s', email, generated)
    return generated


def migrate_credentials(settings):
    """Substitui senhas padrão conhecidas e envolve hashes MD5 em scrypt. Idempotente."""
    changed = False
    for user in User.list_all():
        if not legacy_password.is_raw_md5(user.password):
            continue
        if user.password in KNOWN_DEFAULT_MD5:
            logger.warning('Conta %s usava uma senha padrão pública; senha substituída', user.email)
            user.set_password(seed_password(settings, user.role, user.email))
        else:
            user.password = legacy_password.wrap_md5(user.password)
            logger.info('Hash MD5 de %s envolto em scrypt', user.email)
        changed = True
    if changed:
        db.session.commit()
