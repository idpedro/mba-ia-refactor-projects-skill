const express = require('express');
const config = require('./config');
const { createLogger } = require('./utils/logger');
const { createConnection } = require('./database/connection');
const { initSchema } = require('./database/schema');
const { seed } = require('./database/seed');
const UserModel = require('./models/user.model');
const CourseModel = require('./models/course.model');
const EnrollmentModel = require('./models/enrollment.model');
const PaymentModel = require('./models/payment.model');
const AuditLogModel = require('./models/auditLog.model');
const PasswordService = require('./services/password.service');
const { PaymentService } = require('./services/payment.service');
const ReportService = require('./services/report.service');
const CheckoutController = require('./controllers/checkout.controller');
const ReportController = require('./controllers/report.controller');
const UserController = require('./controllers/user.controller');
const { createAdminAuth } = require('./middlewares/adminAuth');
const { createErrorHandler } = require('./middlewares/errorHandler');
const checkoutRoutes = require('./routes/checkout.routes');
const adminRoutes = require('./routes/admin.routes');
const userRoutes = require('./routes/user.routes');

// Composition root: builds every dependency and wires the layers together.
async function createApp(settings = config) {
    const logger = createLogger(settings.logLevel);
    const db = createConnection(settings.dbPath);
    const passwordService = new PasswordService();

    await initSchema(db);
    await seed(db, passwordService);

    const userModel = new UserModel(db);
    const courseModel = new CourseModel(db);
    const enrollmentModel = new EnrollmentModel(db);
    const paymentModel = new PaymentModel(db);
    const auditLogModel = new AuditLogModel(db);

    const paymentService = new PaymentService({ gatewayKey: settings.paymentGatewayKey, logger });
    const reportService = new ReportService({ paymentModel });

    const checkoutController = new CheckoutController({
        db, courseModel, userModel, enrollmentModel, paymentModel, auditLogModel,
        paymentService, passwordService, logger,
    });
    const reportController = new ReportController({ reportService });
    const userController = new UserController({ db, userModel, logger });

    const adminAuth = createAdminAuth(settings.adminToken);

    const app = express();
    app.use(express.json());
    app.use(checkoutRoutes(checkoutController));
    app.use(adminRoutes(reportController, adminAuth));
    app.use(userRoutes(userController, adminAuth));
    app.use(createErrorHandler(logger));

    return { app, db, logger };
}

async function main() {
    const { app, logger } = await createApp();
    app.listen(config.port, config.host, () => {
        logger.info(`Frankenstein LMS rodando em ${config.host}:${config.port}...`);
    });
}

if (require.main === module) {
    main().catch((err) => {
        console.error('Falha ao iniciar a aplicação:', err);
        process.exit(1);
    });
}

module.exports = { createApp };
