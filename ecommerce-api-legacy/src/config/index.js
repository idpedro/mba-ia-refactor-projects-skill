// Every environment-dependent value. Secrets have no in-code default.
module.exports = {
    port: Number(process.env.PORT) || 3000,
    // Loopback by default; exposing the API on every interface needs HOST=0.0.0.0.
    host: process.env.HOST || '127.0.0.1',
    dbPath: process.env.DB_PATH || ':memory:',
    paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',
    // Admin routes reject every request while this is empty (fail closed).
    adminToken: process.env.ADMIN_TOKEN || '',
    logLevel: process.env.LOG_LEVEL || 'info',
};
