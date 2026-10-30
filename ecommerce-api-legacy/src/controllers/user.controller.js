class UserController {
    constructor({ userModel }) {
        this.users = userModel;
    }

    async delete(id) {
        await this.users.deleteById(id);
    }
}

module.exports = UserController;
