// Configuração por ambiente. Segredos não têm valor literal de fallback:
// senhas ausentes são geradas no seed e impressas uma única vez.
const env = process.env;

module.exports = {
    port: Number(env.PORT) || 3000,
    // Escutar em todas as interfaces é opt-in explícito (HOST=0.0.0.0).
    host: env.HOST || '127.0.0.1',
    dbPath: env.DB_PATH || ':memory:',
    adminEmail: (env.ADMIN_EMAIL || 'admin@fullcycle.com.br').trim().toLowerCase(),
    adminPassword: env.ADMIN_PASSWORD || '',
    seedUserPassword: env.SEED_USER_PASSWORD || '',
};
