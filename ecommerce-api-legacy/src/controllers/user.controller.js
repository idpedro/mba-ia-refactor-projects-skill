class UserController {
    constructor({ db, userModel, logger }) {
        this.db = db;
        this.users = userModel;
        this.logger = logger;
    }

    async deleteUser(id) {
        const removed = await this.db.transaction(() => this.users.deleteWithEnrollments(id));
        this.logger.info(`Remoção do usuário ${id}: ${removed} registro(s) removido(s)`);
        return 'Usuário deletado.';
    }
}

module.exports = { UserController };
