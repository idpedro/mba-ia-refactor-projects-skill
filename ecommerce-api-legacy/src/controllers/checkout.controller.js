const { validateCheckout } = require('../validators/checkout.validator');
const { NotFoundError, PaymentDeclinedError } = require('../errors');
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

        const userId = await this.findOrCreateUser({ name, email, password });

        const status = this.paymentService.charge(card, course.price);
        if (status === PAYMENT_STATUS.DENIED) throw new PaymentDeclinedError();

        const enrollmentId = await this.transaction(async () => {
            const newEnrollmentId = await this.enrollments.create(userId, courseId);
            await this.payments.create(newEnrollmentId, course.price, status);
            await this.auditLogs.record(`Checkout curso ${courseId} por ${userId}`);
            return newEnrollmentId;
        });

        this.cache.set(`last_checkout_${userId}`, course.title);
        return { msg: 'Sucesso', enrollment_id: enrollmentId };
    }

    async findOrCreateUser({ name, email, password }) {
        const existing = await this.users.findIdByEmail(email);
        if (existing) return existing.id;
        const passwordHash = this.passwordService.hash(password || this.passwordService.randomPassword());
        return this.users.create({ name, email, passwordHash });
    }
}

module.exports = CheckoutController;
