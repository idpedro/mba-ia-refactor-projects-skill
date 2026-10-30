const { PAYMENT_STATUS } = require('../services/payment.service');

// Demo data; runs only on an empty database so a file-backed DB_PATH survives restarts.
async function seed(db, passwordService) {
    const { total } = await db.get('SELECT COUNT(*) AS total FROM users');
    if (total > 0) return;

    await db.transaction(async () => {
        await db.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
            ['Leonan', 'leonan@fullcycle.com.br', passwordService.hash('123')]);
        await db.run('INSERT INTO courses (title, price, active) VALUES (?, ?, 1), (?, ?, 1)',
            ['Clean Architecture', 997.0, 'Docker', 497.0]);
        await db.run('INSERT INTO enrollments (user_id, course_id) VALUES (1, 1)');
        await db.run('INSERT INTO payments (enrollment_id, amount, status) VALUES (1, ?, ?)',
            [997.0, PAYMENT_STATUS.PAID]);
    });
}

module.exports = { seed };
