const express = require('express');
const defaultConfig = require('./config');
const logger = require('./utils/logger');
const { createConnection } = require('./database/connection');
const { initSchema } = require('./database/schema');
const { seed } = require('./database/seed');
const { UserModel } = require('./models/user.model');
const { CourseModel } = require('./models/course.model');
const { EnrollmentModel } = require('./models/enrollment.model');
const { PaymentModel } = require('./models/payment.model');
const { AuditLogModel } = require('./models/auditLog.model');
const { PaymentService } = require('./services/payment.service');
const { ReportService } = require('./services/report.service');
const { CheckoutController } = require('./controllers/checkout.controller');
const { ReportController } = require('./controllers/report.controller');
const { UserController } = require('./controllers/user.controller');
const { createAuth } = require('./middlewares/auth');
const { createErrorHandler } = require('./middlewares/errorHandler');
const checkoutRoutes = require('./routes/checkout.routes');
const adminRoutes = require('./routes/admin.routes');
const userRoutes = require('./routes/user.routes');

// Composition root: monta banco, models, services, controllers e rotas.
async function createApp(config = defaultConfig) {
    const db = createConnection(config.dbPath);
    await initSchema(db);
    await seed(db, config, logger);

    const models = {
        userModel: new UserModel(db),
        courseModel: new CourseModel(db),
        enrollmentModel: new EnrollmentModel(db),
        paymentModel: new PaymentModel(db),
        auditLogModel: new AuditLogModel(db),
    };
    const paymentService = new PaymentService({ logger });
    const reportService = new ReportService(models);
    const auth = createAuth({ db, userModel: models.userModel });

    const checkoutController = new CheckoutController({ db, ...models, paymentService, logger });
    const reportController = new ReportController({ db, reportService });
    const userController = new UserController({ db, userModel: models.userModel, logger });

    const app = express();
    app.use(express.json());
    app.use(checkoutRoutes({ checkoutController, auth }));
    app.use(adminRoutes({ reportController, auth }));
    app.use(userRoutes({ userController, auth }));
    app.use(createErrorHandler(logger));

    return { app, db, models };
}

function start(config = defaultConfig) {
    return createApp(config).then(({ app }) => {
        const server = app.listen(config.port, config.host, () => {
            logger.info(`Frankenstein LMS rodando em http://${config.host}:${config.port}`);
        });
        server.on('error', (err) => {
            logger.error(`Falha ao escutar em ${config.host}:${config.port}`, err);
            process.exitCode = 1;
        });
        return server;
    });
}

if (require.main === module) {
    start().catch((err) => {
        logger.error('Falha ao iniciar a aplicação', err);
        process.exitCode = 1;
    });
}

module.exports = { createApp, start };
