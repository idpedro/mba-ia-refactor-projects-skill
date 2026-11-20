const { ROLE_ADMIN } = require('../constants/roles');
const { PAYMENT_STATUS } = require('../services/payment.service');
const { hashPassword, isHashed, generatePassword } = require('../services/password.service');

const SEED_USER = { name: 'Leonan', email: 'leonan@fullcycle.com.br' };
const SEED_COURSES = [
    { title: 'Clean Architecture', price: 997.0 },
    { title: 'Docker', price: 497.0 },
];

// Senha vinda do ambiente, ou gerada e impressa uma única vez.
function resolvePassword(fromEnv, email, envName, logger) {
    if (fromEnv) return fromEnv;
    const generated = generatePassword();
    logger.info(`Senha gerada para ${email}: ${generated} (defina ${envName} para fixá-la)`);
    return generated;
}

async function seedCatalog(db, config, logger) {
    const { total } = await db.get('SELECT COUNT(*) AS total FROM courses');
    if (total > 0) return;

    for (const course of SEED_COURSES) {
        await db.run('INSERT INTO courses (title, price, active) VALUES (?, ?, 1)', [course.title, course.price]);
    }
    const password = resolvePassword(config.seedUserPassword, SEED_USER.email, 'SEED_USER_PASSWORD', logger);
    const user = await db.run(
        'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
        [SEED_USER.name, SEED_USER.email, await hashPassword(password)],
    );
    const firstCourse = await db.get('SELECT id, price FROM courses ORDER BY id LIMIT 1');
    const enrollment = await db.run('INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)', [user.lastID, firstCourse.id]);
    await db.run(
        'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
        [enrollment.lastID, firstCourse.price, PAYMENT_STATUS.PAID],
    );
}

async function seedAdmin(db, config, logger) {
    const existing = await db.get('SELECT id, role FROM users WHERE email = ?', [config.adminEmail]);
    if (existing) {
        if (existing.role !== ROLE_ADMIN) {
            logger.warn(`${config.adminEmail} já existe sem papel admin; não foi promovido automaticamente`);
        }
        return;
    }
    const password = resolvePassword(config.adminPassword, config.adminEmail, 'ADMIN_PASSWORD', logger);
    await db.run(
        'INSERT INTO users (name, email, pass, role) VALUES (?, ?, ?, ?)',
        ['Administrador', config.adminEmail, await hashPassword(password), ROLE_ADMIN],
    );
}

// Bancos criados pelo código original guardam senhas em texto puro ou no
// formato inseguro antigo (inclusive a senha padrão conhecida do seed). Nenhuma
// delas é mantida: cada conta recebe uma senha nova.
async function replaceLegacyPasswords(db, config, logger) {
    const users = await db.all('SELECT id, email, pass FROM users');
    for (const user of users) {
        if (isHashed(user.pass)) continue;
        const fromEnv = user.email === SEED_USER.email ? config.seedUserPassword
            : user.email === config.adminEmail ? config.adminPassword : '';
        const envName = user.email === SEED_USER.email ? 'SEED_USER_PASSWORD' : 'ADMIN_PASSWORD';
        logger.warn(`Senha em formato legado substituída para ${user.email}`);
        const password = resolvePassword(fromEnv, user.email, envName, logger);
        await db.run('UPDATE users SET pass = ? WHERE id = ?', [await hashPassword(password), user.id]);
    }
}

async function seed(db, config, logger) {
    await replaceLegacyPasswords(db, config, logger);
    await seedCatalog(db, config, logger);
    await seedAdmin(db, config, logger);
}

module.exports = { seed };
