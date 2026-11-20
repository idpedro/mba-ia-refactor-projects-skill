const { ROLE_STUDENT } = require('../constants/roles');

class UserModel {
    constructor(db) {
        this.db = db;
    }

    findByEmail(email) {
        return this.db.get('SELECT id, name, email, pass, role FROM users WHERE email = ? COLLATE NOCASE', [email]);
    }

    async create({ name, email, passwordHash }) {
        const { lastID } = await this.db.run(
            'INSERT INTO users (name, email, pass, role) VALUES (?, ?, ?, ?)',
            [name, email, passwordHash, ROLE_STUDENT],
        );
        return lastID;
    }

    // Remove o usuário e o que depende dele; deve rodar dentro de uma transação.
    async deleteWithEnrollments(id) {
        await this.db.run(
            'DELETE FROM payments WHERE enrollment_id IN (SELECT id FROM enrollments WHERE user_id = ?)',
            [id],
        );
        await this.db.run('DELETE FROM enrollments WHERE user_id = ?', [id]);
        const { changes } = await this.db.run('DELETE FROM users WHERE id = ?', [id]);
        return changes;
    }
}

module.exports = { UserModel };
