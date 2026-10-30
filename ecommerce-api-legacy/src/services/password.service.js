const crypto = require('crypto');

const SALT_BYTES = 16;
const KEY_LENGTH = 64;
const RANDOM_PASSWORD_BYTES = 32;

class PasswordService {
    hash(raw) {
        const salt = crypto.randomBytes(SALT_BYTES).toString('hex');
        const hash = crypto.scryptSync(raw, salt, KEY_LENGTH).toString('hex');
        return `${salt}:${hash}`;
    }

    verify(raw, stored) {
        const [salt, hash] = String(stored).split(':');
        if (!salt || !hash) return false;
        const candidate = crypto.scryptSync(raw, salt, KEY_LENGTH);
        const expected = Buffer.from(hash, 'hex');
        return expected.length === candidate.length && crypto.timingSafeEqual(candidate, expected);
    }

    // Used when a checkout creates an account without a password: nobody knows it.
    randomPassword() {
        return crypto.randomBytes(RANDOM_PASSWORD_BYTES).toString('hex');
    }
}

module.exports = PasswordService;
