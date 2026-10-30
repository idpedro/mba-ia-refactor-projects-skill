// Every environment-dependent value lives here. Secrets come only from the environment.
module.exports = {
    port: Number(process.env.PORT) || 3000,
    dbPath: process.env.DB_PATH || ':memory:',
    paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',
    adminToken: process.env.ADMIN_TOKEN || '',
    logLevel: process.env.LOG_LEVEL || 'info',
};
