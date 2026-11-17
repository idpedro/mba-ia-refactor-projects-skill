// Domain errors. The message is the exact plain-text body clients already receive.
class AppError extends Error {
    constructor(message, status = 500) {
        super(message);
        this.name = this.constructor.name;
        this.status = status;
    }
}

class BadRequestError extends AppError {
    constructor(message = 'Bad Request') { super(message, 400); }
}

class UnauthorizedError extends AppError {
    constructor(message = 'Unauthorized') { super(message, 401); }
}

class NotFoundError extends AppError {
    constructor(message) { super(message, 404); }
}

class PaymentDeniedError extends AppError {
    constructor(message = 'Pagamento recusado') { super(message, 400); }
}

module.exports = { AppError, BadRequestError, UnauthorizedError, NotFoundError, PaymentDeniedError };
