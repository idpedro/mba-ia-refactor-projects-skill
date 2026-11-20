const { AppError } = require('../errors');

const GENERIC_MESSAGE = 'Erro interno do servidor';
const UNIQUE_VIOLATION = /UNIQUE constraint failed/;

// Respostas de erro em texto puro, como no contrato original.
function createErrorHandler(logger) {
    return function errorHandler(err, req, res, next) { // eslint-disable-line no-unused-vars
        if (err instanceof AppError) return res.status(err.status).send(err.message);

        if (err && err.code === 'SQLITE_CONSTRAINT' && UNIQUE_VIOLATION.test(err.message)) {
            return res.status(409).send('Conflito');
        }
        // Erros do body parser (JSON malformado, corpo grande demais).
        if (err && err.type && Number.isInteger(err.status) && err.status >= 400 && err.status < 500) {
            return res.status(err.status).send('Bad Request');
        }

        logger.error(`Erro inesperado em ${req.method} ${req.originalUrl}`, err);
        return res.status(500).send(GENERIC_MESSAGE);
    };
}

module.exports = { createErrorHandler };
