const crypto = require('crypto');

const SALT_BYTES = 16;
const KEY_LENGTH = 64;

// Salted scrypt hashes stored as "salt:hash" (hex).
class PasswordService {
    hash(raw) {
        const salt = crypto.randomBytes(SALT_BYTES).toString('hex');
        const hash = crypto.scryptSync(raw, salt, KEY_LENGTH).toString('hex');
        return `${salt}:${hash}`;
    }

    verify(raw, stored) {
        if (typeof raw !== 'string' || typeof stored !== 'string') return false;
        const [salt, hash] = stored.split(':');
        if (!salt || !hash) return false;
        const expected = Buffer.from(hash, 'hex');
        const candidate = crypto.scryptSync(raw, salt, expected.length);
        return crypto.timingSafeEqual(candidate, expected);
    }
}

module.exports = PasswordService;
