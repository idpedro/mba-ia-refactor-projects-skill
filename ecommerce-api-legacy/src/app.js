// Composition root: builds config, database, models, services, controllers and routes.
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
const CacheService = require('./services/cache.service');
const { PaymentService } = require('./services/payment.service');
const ReportService = require('./services/report.service');

const CheckoutController = require('./controllers/checkout.controller');
const ReportController = require('./controllers/report.controller');
const UserController = require('./controllers/user.controller');

const checkoutRoutes = require('./routes/checkout.routes');
const adminRoutes = require('./routes/admin.routes');
const userRoutes = require('./routes/user.routes');
const { createAdminAuth } = require('./middlewares/adminAuth');
const { createErrorHandler } = require('./middlewares/errorHandler');

async function buildApp(settings = config) {
    const logger = createLogger(settings.logLevel);
    const db = createConnection(settings.dbPath);
    const passwordService = new PasswordService();

    await initSchema(db);
    await seed(db, passwordService);

    const userModel = new UserModel(db);
    const courseModel = new CourseModel(db);

    const checkoutController = new CheckoutController({
        transaction: (work) => db.transaction(work),
        userModel,
        courseModel,
        enrollmentModel: new EnrollmentModel(db),
        paymentModel: new PaymentModel(db),
        auditLogModel: new AuditLogModel(db),
        paymentService: new PaymentService({ gatewayKey: settings.paymentGatewayKey, logger }),
        passwordService,
        cacheService: new CacheService(logger),
    });
    const reportController = new ReportController({ reportService: new ReportService({ courseModel }) });
    const userController = new UserController({ userModel });
    const adminAuth = createAdminAuth(settings.adminToken);

    const app = express();
    app.use(express.json());
    app.use(checkoutRoutes(checkoutController));
    app.use(adminRoutes(reportController, adminAuth));
    app.use(userRoutes(userController, adminAuth));
    app.use(createErrorHandler(logger));

    return { app, db, logger };
}

if (require.main === module) {
    buildApp()
        .then(({ app, logger }) => {
            app.listen(config.port, () => logger.info(`Frankenstein LMS rodando na porta ${config.port}...`));
        })
        .catch((err) => {
            console.error('Failed to start application', err);
            process.exit(1);
        });
}

module.exports = { buildApp };
