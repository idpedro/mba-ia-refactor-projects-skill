class UserController {
    constructor({ userModel }) {
        this.users = userModel;
    }

    async remove(id) {
        await this.users.deleteWithDependents(id);
        return 'Usuário deletado.';
    }
}

module.exports = UserController;
