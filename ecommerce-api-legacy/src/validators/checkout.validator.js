const { BadRequestError } = require('../errors');

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+$/;

const isNonEmptyString = (value) => typeof value === 'string' && value.length > 0;

// Request fields keep their public names (usr, eml, pwd, c_id, card);
// the returned object uses readable internal names.
function validateCheckout(body) {
    if (body === null || typeof body !== 'object') throw new BadRequestError();

    const { usr: name, eml: email, pwd: password, c_id: courseId, card } = body;

    if (!isNonEmptyString(name) || !isNonEmptyString(email) || !isNonEmptyString(card)) {
        throw new BadRequestError();
    }
    if (courseId === undefined || courseId === null || courseId === '' || typeof courseId === 'object') {
        throw new BadRequestError();
    }
    if (!EMAIL_PATTERN.test(email)) throw new BadRequestError();
    if (password !== undefined && password !== null && typeof password !== 'string') {
        throw new BadRequestError();
    }

    return { name, email, password: password || null, courseId, card };
}

function validateUserId(rawId) {
    if (!/^\d+$/.test(String(rawId))) throw new BadRequestError();
    return Number(rawId);
}

module.exports = { validateCheckout, validateUserId };
