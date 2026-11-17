const crypto = require('crypto');
const { promisify } = require('util');

const scrypt = promisify(crypto.scrypt);

const SALT_BYTES = 16;
const KEY_LENGTH = 64;

// Salted scrypt, stored as "salt:hash" (both hex).
class PasswordService {
    async hash(raw) {
        const salt = crypto.randomBytes(SALT_BYTES).toString('hex');
        const derived = await scrypt(raw, salt, KEY_LENGTH);
        return `${salt}:${derived.toString('hex')}`;
    }

    async verify(raw, stored) {
        const [salt, hash] = String(stored || '').split(':');
        if (!salt || !hash) return false;
        const expected = Buffer.from(hash, 'hex');
        const candidate = await scrypt(raw, salt, expected.length);
        return crypto.timingSafeEqual(candidate, expected);
    }

    // Used for accounts created at checkout without a password: nobody knows it.
    hashUnknownSecret() {
        return this.hash(crypto.randomBytes(32).toString('hex'));
    }
}

module.exports = PasswordService;
