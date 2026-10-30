const { PAYMENT_STATUS } = require('../services/payment.service');

// Seeds run only on an empty database (always the case for ':memory:').
async function seed(db, passwordService) {
    const { count } = await db.get('SELECT COUNT(*) AS count FROM users');
    if (count > 0) return;

    await db.transaction(async () => {
        await db.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
            ['Leonan', 'leonan@fullcycle.com.br', passwordService.hash('123')]);
        await db.run('INSERT INTO courses (title, price, active) VALUES (?, ?, 1), (?, ?, 1)',
            ['Clean Architecture', 997.0, 'Docker', 497.0]);
        await db.run('INSERT INTO enrollments (user_id, course_id) VALUES (1, 1)');
        await db.run('INSERT INTO payments (enrollment_id, amount, status) VALUES (1, 997.00, ?)',
            [PAYMENT_STATUS.PAID]);
    });
}

module.exports = { seed };
