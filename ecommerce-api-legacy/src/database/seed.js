// Initial data. Skipped when the database already has users (file-backed DB_PATH).
async function seed(db, passwordService) {
    const existing = await db.get('SELECT COUNT(*) AS total FROM users');
    if (existing.total > 0) return;

    const passwordHash = await passwordService.hash('123');
    await db.transaction(async (tx) => {
        await tx.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
            ['Leonan', 'leonan@fullcycle.com.br', passwordHash]);
        await tx.run('INSERT INTO courses (title, price, active) VALUES (?, ?, ?), (?, ?, ?)',
            ['Clean Architecture', 997.0, 1, 'Docker', 497.0, 1]);
        await tx.run('INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)', [1, 1]);
        await tx.run('INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)', [1, 997.0, 'PAID']);
    });
}

module.exports = { seed };
