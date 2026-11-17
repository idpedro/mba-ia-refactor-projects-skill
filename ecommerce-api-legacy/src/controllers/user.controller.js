const { validateUserId } = require('../validators/checkout.validator');

const DELETED_MESSAGE = 'Usuário deletado, junto com as matrículas e pagamentos relacionados.';

class UserController {
    constructor({ db, userModel, logger }) {
        this.db = db;
        this.users = userModel;
        this.logger = logger;
    }

    // Idempotent like before: an unknown id still answers success.
    async deleteUser(rawId) {
        const id = validateUserId(rawId);
        await this.db.transaction((tx) => this.users.deleteWithRelated(id, tx));
        this.logger.info(`Usuário ${id} removido com matrículas e pagamentos`);
        return DELETED_MESSAGE;
    }
}

module.exports = UserController;
