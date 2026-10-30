const { AppError } = require('../errors');

// Central error handler. Error bodies stay plain text, as in the original API.
function createErrorHandler(logger) {
    // eslint-disable-next-line no-unused-vars
    return (err, req, res, next) => {
        const status = err.status || err.statusCode || 500;
        if (status >= 500) {
            logger.error(err.stack || err);
            return res.status(500).send('Erro interno do servidor');
        }
        // Domain errors carry the original messages; framework errors (e.g. malformed JSON) stay generic.
        return res.status(status).send(err instanceof AppError ? err.message : 'Bad Request');
    };
}

module.exports = { createErrorHandler };
