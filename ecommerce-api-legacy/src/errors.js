// Domain errors; the error middleware turns them into plain-text responses.
class AppError extends Error {
    constructor(message, status = 500) {
        super(message);
        this.name = this.constructor.name;
        this.status = status;
    }
}

class ValidationError extends AppError {
    constructor(message = 'Bad Request') { super(message, 400); }
}

class UnauthorizedError extends AppError {
    constructor(message = 'Não autorizado') { super(message, 401); }
}

class NotFoundError extends AppError {
    constructor(message) { super(message, 404); }
}

class PaymentDeclinedError extends AppError {
    constructor(message = 'Pagamento recusado') { super(message, 400); }
}

module.exports = { AppError, ValidationError, UnauthorizedError, NotFoundError, PaymentDeclinedError };
