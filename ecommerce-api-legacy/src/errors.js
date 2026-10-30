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

class NotFoundError extends AppError {
    constructor(message) { super(message, 404); }
}

class PaymentDeclinedError extends AppError {
    constructor(message = 'Pagamento recusado') { super(message, 400); }
}

module.exports = { AppError, ValidationError, NotFoundError, PaymentDeclinedError };
