const { NotFoundError, PaymentDeniedError } = require('../errors');
const { PAYMENT_STATUS } = require('../services/payment.service');
const { validateCheckout } = require('../validators/checkout.validator');

class CheckoutController {
    constructor({ db, courseModel, userModel, enrollmentModel, paymentModel, auditLogModel,
        paymentService, passwordService, logger }) {
        this.db = db;
        this.courses = courseModel;
        this.users = userModel;
        this.enrollments = enrollmentModel;
        this.payments = paymentModel;
        this.auditLogs = auditLogModel;
        this.paymentService = paymentService;
        this.passwordService = passwordService;
        this.logger = logger;
    }

    async checkout(body) {
        const { name, email, password, courseId, card } = validateCheckout(body);

        const course = await this.courses.findActiveById(courseId);
        if (!course) throw new NotFoundError('Curso não encontrado');

        // Charge first: a denied card must not leave a user behind.
        const status = this.paymentService.charge(card);
        if (status === PAYMENT_STATUS.DENIED) throw new PaymentDeniedError();

        // Hashed outside the transaction so scrypt never holds the write lock.
        const passwordHash = password
            ? await this.passwordService.hash(password)
            : await this.passwordService.hashUnknownSecret();

        const { userId, enrollmentId } = await this.db.transaction(async (tx) => {
            const existing = await this.users.findByEmail(email, tx);
            const id = existing
                ? existing.id
                : await this.users.create({ name, email, passwordHash }, tx);

            const enrollment = await this.enrollments.create({ userId: id, courseId }, tx);
            await this.payments.create({ enrollmentId: enrollment, amount: course.price, status }, tx);
            await this.auditLogs.record(`Checkout curso ${courseId} por ${id}`, tx);
            return { userId: id, enrollmentId: enrollment };
        });

        this.logger.info(`Checkout do curso ${courseId} pelo usuário ${userId}`);
        return { msg: 'Sucesso', enrollment_id: enrollmentId };
    }
}

module.exports = CheckoutController;
