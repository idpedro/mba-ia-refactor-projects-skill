class UserModel {
    constructor(db) {
        this.db = db;
    }

    findByEmail(email, executor = this.db) {
        return executor.get('SELECT id FROM users WHERE email = ?', [email]);
    }

    async create({ name, email, passwordHash }, executor = this.db) {
        const { lastID } = await executor.run(
            'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', [name, email, passwordHash]);
        return lastID;
    }

    // Removes the user together with its enrollments and their payments.
    // Callers wrap it in a transaction so nothing is left orphaned.
    async deleteWithRelated(id, executor = this.db) {
        await executor.run(
            'DELETE FROM payments WHERE enrollment_id IN (SELECT id FROM enrollments WHERE user_id = ?)', [id]);
        await executor.run('DELETE FROM enrollments WHERE user_id = ?', [id]);
        const { changes } = await executor.run('DELETE FROM users WHERE id = ?', [id]);
        return changes;
    }
}

module.exports = UserModel;
