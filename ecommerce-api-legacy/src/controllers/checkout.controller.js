const { validateCheckout } = require('../validators/checkout.validator');
const { NotFoundError, PaymentDeclinedError, UnauthorizedError, ValidationError } = require('../errors');
const { PAYMENT_STATUS } = require('../services/payment.service');

class CheckoutController {
    constructor({ transaction, userModel, courseModel, enrollmentModel, paymentModel, auditLogModel,
        paymentService, passwordService, cacheService }) {
        this.transaction = transaction;
        this.users = userModel;
        this.courses = courseModel;
        this.enrollments = enrollmentModel;
        this.payments = paymentModel;
        this.auditLogs = auditLogModel;
        this.paymentService = paymentService;
        this.passwordService = passwordService;
        this.cache = cacheService;
    }

    async checkout(body) {
        const { name, email, password, courseId, card } = validateCheckout(body);

        const course = await this.courses.findActiveById(courseId);
        if (!course) throw new NotFoundError('Curso não encontrado');

        const existingUser = await this.users.findByEmail(email);
        if (existingUser && !this.passwordService.verify(password, existingUser.pass)) {
            throw new UnauthorizedError('Credenciais inválidas');
        }
        if (!existingUser && !password) throw new ValidationError();

        // Decided before any write, so a declined card leaves nothing behind.
        const status = this.paymentService.charge(card, course.price);
        if (status !== PAYMENT_STATUS.PAID) throw new PaymentDeclinedError();

        const { userId, enrollmentId } = await this.transaction(async () => {
            const userId = existingUser
                ? existingUser.id
                : await this.users.create({ name, email, passwordHash: this.passwordService.hash(password) });
            const enrollmentId = await this.enrollments.create(userId, course.id);
            await this.payments.create(enrollmentId, course.price, status);
            await this.auditLogs.record(`Checkout curso ${course.id} por ${userId}`);
            return { userId, enrollmentId };
        });

        this.cache.set(`last_checkout_${userId}`, course.title);
        return { enrollmentId };
    }
}

module.exports = CheckoutController;
