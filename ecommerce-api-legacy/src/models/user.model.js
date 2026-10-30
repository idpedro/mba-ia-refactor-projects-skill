class UserModel {
    constructor(db) {
        this.db = db;
    }

    findByEmail(email) {
        return this.db.get('SELECT id, name, email, pass FROM users WHERE email = ?', [email]);
    }

    async create({ name, email, passwordHash }) {
        const { lastID } = await this.db.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', [name, email, passwordHash]);
        return lastID;
    }

    // Removes the user with their enrollments and payments in one transaction, leaving no orphans.
    deleteById(id) {
        return this.db.transaction(async () => {
            await this.db.run(
                'DELETE FROM payments WHERE enrollment_id IN (SELECT id FROM enrollments WHERE user_id = ?)', [id]);
            await this.db.run('DELETE FROM enrollments WHERE user_id = ?', [id]);
            const { changes } = await this.db.run('DELETE FROM users WHERE id = ?', [id]);
            return changes;
        });
    }
}

module.exports = UserModel;
