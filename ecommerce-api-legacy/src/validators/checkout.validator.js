const { ValidationError } = require('../errors');

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const CARD_PATTERN = /^\d{12,19}$/;
const NUMERIC_ID_PATTERN = /^\d+$/;

function parseCourseId(value) {
    const id = typeof value === 'string' && NUMERIC_ID_PATTERN.test(value) ? Number(value) : value;
    if (typeof id !== 'number' || !Number.isFinite(id) || !Number.isInteger(id) || id <= 0) {
        throw new ValidationError('Curso inválido');
    }
    return id;
}

// Campos públicos do contrato: usr, eml, pwd, c_id, card.
function validateCheckout(body) {
    if (!body || typeof body !== 'object' || Array.isArray(body)) throw new ValidationError();
    const { usr: name, eml: email, pwd: password, c_id: courseId, card } = body;

    // Mesma regra de presença (e mesma mensagem) do contrato original.
    if (!name || !email || !courseId || !card) throw new ValidationError();

    if (typeof name !== 'string' || !name.trim()) throw new ValidationError('Nome inválido');
    if (typeof email !== 'string' || !EMAIL_PATTERN.test(email.trim())) throw new ValidationError('E-mail inválido');
    const hasPassword = password !== undefined && password !== null && password !== '';
    if (hasPassword && typeof password !== 'string') throw new ValidationError('Senha inválida');
    if (typeof card !== 'string' || !CARD_PATTERN.test(card)) throw new ValidationError('Cartão inválido');

    return {
        name: name.trim(),
        email: email.trim().toLowerCase(),
        password: hasPassword ? password : null,
        courseId: parseCourseId(courseId),
        card,
    };
}

module.exports = { validateCheckout };
