const { AppError } = require('../errors');

// Single place that turns errors into responses. Bodies stay plain text, as in the original API.
function createErrorHandler(logger) {
    // eslint-disable-next-line no-unused-vars
    return (err, req, res, next) => {
        if (err instanceof AppError) {
            return res.status(err.status).type('text').send(err.message);
        }
        if (err.type === 'entity.parse.failed') {
            return res.status(400).type('text').send('Bad Request');
        }
        logger.error(`${req.method} ${req.originalUrl} falhou:`, err);
        return res.status(500).type('text').send('Erro interno');
    };
}

module.exports = { createErrorHandler };
