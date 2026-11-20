class AppError extends Error {
    constructor(message, status) {
        super(message);
        this.status = status;
    }
}

class ValidationError extends AppError {
    constructor(message = 'Bad Request') { super(message, 400); }
}

class UnauthorizedError extends AppError {
    constructor(message = 'Não autenticado') { super(message, 401); }
}

class ForbiddenError extends AppError {
    constructor(message = 'Acesso negado') { super(message, 403); }
}

class NotFoundError extends AppError {
    constructor(message) { super(message, 404); }
}

class ConflictError extends AppError {
    constructor(message = 'Conflito') { super(message, 409); }
}

module.exports = { AppError, ValidationError, UnauthorizedError, ForbiddenError, NotFoundError, ConflictError };
