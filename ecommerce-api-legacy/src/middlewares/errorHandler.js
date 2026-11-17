const { AppError } = require('../errors');

const INTERNAL_ERROR_TEXT = 'Erro interno';
const BAD_REQUEST_TEXT = 'Bad Request';

// Plain-text bodies, as the clients already expect. Unexpected errors answer
// a generic 500 and only the log gets the detail.
function createErrorHandler(logger) {
    // eslint-disable-next-line no-unused-vars
    return (err, req, res, next) => {
        if (err instanceof AppError && err.status < 500) {
            return res.status(err.status).send(err.message);
        }
        // Malformed JSON body or other client-side errors raised by Express.
        if (Number.isInteger(err.status) && err.status >= 400 && err.status < 500) {
            return res.status(err.status).send(err.status === 400 ? BAD_REQUEST_TEXT : err.message);
        }
        logger.error(`${req.method} ${req.originalUrl}: ${err.stack || err}`);
        return res.status(500).send(INTERNAL_ERROR_TEXT);
    };
}

module.exports = { createErrorHandler };
