const { validateCheckout } = require('../validators/checkout.validator');
const { PAYMENT_STATUS } = require('../services/payment.service');
const { hashPassword, verifyPassword, generatePassword } = require('../services/password.service');
const { ROLE_ADMIN } = require('../constants/roles');
const { NotFoundError, ForbiddenError, ValidationError } = require('../errors');

class CheckoutController {
    constructor({ db, userModel, courseModel, enrollmentModel, paymentModel, auditLogModel, paymentService, logger }) {
        this.db = db;
        this.users = userModel;
        this.courses = courseModel;
        this.enrollments = enrollmentModel;
        this.payments = paymentModel;
        this.auditLogs = auditLogModel;
        this.paymentService = paymentService;
        this.logger = logger;
    }

    // `actor` é o usuário autenticado (Basic) ou null para checkout anônimo.
    async checkout(body, actor) {
        const input = validateCheckout(body);

        return this.db.transaction(async () => {
            const course = await this.courses.findActiveById(input.courseId);
            if (!course) throw new NotFoundError('Curso não encontrado');

            const existing = await this.users.findByEmail(input.email);
            await this.assertCanEnroll(actor, existing, input);

            const status = this.paymentService.charge(input.card, course.price);
            if (status !== PAYMENT_STATUS.PAID) throw new ValidationError('Pagamento recusado');

            const userId = existing ? existing.id : await this.users.create({
                name: input.name,
                email: input.email,
                passwordHash: await hashPassword(input.password ?? generatePassword()),
            });
            const enrollmentId = await this.enrollments.create(userId, course.id);
            await this.payments.create(enrollmentId, course.price, status);
            await this.auditLogs.record(`Checkout curso ${course.id} por ${userId}`);

            this.logger.info(`Checkout concluído: curso ${course.id}, usuário ${userId}, matrícula ${enrollmentId}`);
            return { msg: 'Sucesso', enrollment_id: enrollmentId };
        });
    }

    // O dono da matrícula vem da credencial, nunca só do e-mail no corpo.
    async assertCanEnroll(actor, existing, input) {
        if (actor && actor.role === ROLE_ADMIN) return;
        if (actor) {
            if (actor.email !== input.email) throw new ForbiddenError('Acesso negado');
            return;
        }
        if (existing && !(await verifyPassword(input.password, existing.pass))) {
            throw new ForbiddenError('Acesso negado');
        }
    }
}

module.exports = { CheckoutController };
