const { ValidationError } = require('../errors');

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const CARD_PATTERN = /^\d+$/;

const isNonEmptyString = (value) => typeof value === 'string' && value.trim() !== '';

function parseCourseId(value) {
    const id = typeof value === 'string' && /^\d+$/.test(value) ? Number(value) : value;
    return Number.isInteger(id) && id > 0 ? id : null;
}

// Maps the public request fields (usr, eml, pwd, c_id, card) to internal names.
function validateCheckout(body) {
    const { usr: name, eml: email, pwd: password, c_id: rawCourseId, card } = body || {};
    const courseId = parseCourseId(rawCourseId);

    if (!isNonEmptyString(name) || !isNonEmptyString(email) || !EMAIL_PATTERN.test(email)
        || courseId === null || !isNonEmptyString(card) || !CARD_PATTERN.test(card)
        || (password !== undefined && password !== null && typeof password !== 'string')) {
        throw new ValidationError();
    }

    return { name, email, password: password || null, courseId, card };
}

module.exports = { validateCheckout };
