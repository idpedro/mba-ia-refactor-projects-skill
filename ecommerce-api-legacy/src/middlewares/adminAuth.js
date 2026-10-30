const crypto = require('crypto');

const BEARER_PREFIX = 'Bearer ';

function tokensMatch(given, expected) {
    const a = Buffer.from(given);
    const b = Buffer.from(expected);
    return a.length === b.length && crypto.timingSafeEqual(a, b);
}

// Admin routes require `Authorization: Bearer <ADMIN_TOKEN>`; with no token configured they stay closed.
function createAdminAuth(adminToken) {
    return (req, res, next) => {
        const header = req.get('authorization') || '';
        const given = header.startsWith(BEARER_PREFIX) ? header.slice(BEARER_PREFIX.length) : '';
        if (!adminToken || !given || !tokensMatch(given, adminToken)) {
            return res.status(403).json({ error: 'Forbidden' });
        }
        return next();
    };
}

module.exports = { createAdminAuth };
