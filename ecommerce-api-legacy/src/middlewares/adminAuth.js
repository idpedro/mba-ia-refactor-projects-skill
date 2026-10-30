const crypto = require('crypto');
const { UnauthorizedError } = require('../errors');

const digest = (value) => crypto.createHash('sha256').update(value).digest();

// Static admin token from config, sent as "Authorization: Bearer <token>".
// With no token configured every request is rejected (fail closed).
function createAdminAuth(adminToken) {
    const expected = adminToken ? digest(adminToken) : null;

    return (req, res, next) => {
        const header = req.get('Authorization') || '';
        const provided = header.startsWith('Bearer ') ? header.slice('Bearer '.length) : '';
        if (!expected || !provided || !crypto.timingSafeEqual(digest(provided), expected)) {
            return next(new UnauthorizedError());
        }
        return next();
    };
}

module.exports = { createAdminAuth };
