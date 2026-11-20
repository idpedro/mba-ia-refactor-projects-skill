const { ROLE_STUDENT } = require('../constants/roles');

// Idempotente: cria as tabelas num banco novo e migra um banco criado pelo
// código original (sem coluna `role`, sem unicidade de e-mail).
async function initSchema(db) {
    await db.run('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, pass TEXT)');
    await db.run('CREATE TABLE IF NOT EXISTS courses (id INTEGER PRIMARY KEY, title TEXT, price REAL, active INTEGER)');
    await db.run('CREATE TABLE IF NOT EXISTS enrollments (id INTEGER PRIMARY KEY, user_id INTEGER, course_id INTEGER)');
    await db.run('CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY, enrollment_id INTEGER, amount REAL, status TEXT)');
    await db.run('CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY, action TEXT, created_at DATETIME)');

    const columns = await db.all('PRAGMA table_info(users)');
    if (!columns.some((column) => column.name === 'role')) {
        await db.run(`ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT '${ROLE_STUDENT}'`);
    }

    await db.run('UPDATE users SET email = lower(trim(email)) WHERE email <> lower(trim(email))');
    await db.run('CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_nocase ON users (email COLLATE NOCASE)');
    await db.run('CREATE INDEX IF NOT EXISTS idx_enrollments_course ON enrollments (course_id)');
    await db.run('CREATE INDEX IF NOT EXISTS idx_payments_enrollment ON payments (enrollment_id)');
}

module.exports = { initSchema };
