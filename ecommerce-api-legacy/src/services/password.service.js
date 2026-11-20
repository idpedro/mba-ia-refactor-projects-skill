const crypto = require('crypto');
const { promisify } = require('util');

const scrypt = promisify(crypto.scrypt);
const SALT_BYTES = 16;
const KEY_LENGTH = 64;
const HASH_FORMAT = /^[0-9a-f]{32}:[0-9a-f]{128}$/;

async function hashPassword(raw) {
    const salt = crypto.randomBytes(SALT_BYTES).toString('hex');
    const key = await scrypt(raw, salt, KEY_LENGTH);
    return `${salt}:${key.toString('hex')}`;
}

async function verifyPassword(raw, stored) {
    if (typeof raw !== 'string' || !isHashed(stored)) return false;
    const [salt, hash] = stored.split(':');
    const candidate = await scrypt(raw, salt, KEY_LENGTH);
    return crypto.timingSafeEqual(candidate, Buffer.from(hash, 'hex'));
}

function isHashed(stored) {
    return typeof stored === 'string' && HASH_FORMAT.test(stored);
}

function generatePassword() {
    return crypto.randomBytes(12).toString('hex');
}

module.exports = { hashPassword, verifyPassword, isHashed, generatePassword };
