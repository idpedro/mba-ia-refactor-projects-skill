const { ValidationError } = require('../errors');

const isNonEmptyString = (value) => typeof value === 'string' && value.trim() !== '';

// Public request fields keep their original names (usr, eml, pwd, c_id, card).
function validateCheckout(body) {
    if (!body || typeof body !== 'object') throw new ValidationError();
    const { usr: name, eml: email, pwd: password, c_id: rawCourseId, card } = body;

    if (!isNonEmptyString(name) || !isNonEmptyString(email) || !isNonEmptyString(card)) {
        throw new ValidationError();
    }
    const courseId = Number(rawCourseId);
    if (!rawCourseId || !Number.isInteger(courseId) || courseId <= 0) throw new ValidationError();
    if (password !== undefined && password !== null && password !== '' && typeof password !== 'string') {
        throw new ValidationError();
    }

    return { name, email, password: password || null, courseId, card };
}

module.exports = { validateCheckout };
