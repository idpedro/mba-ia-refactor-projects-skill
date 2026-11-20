const express = require('express');
const asyncHandler = require('../middlewares/asyncHandler');

module.exports = function userRoutes({ userController, auth }) {
    const router = express.Router();

    async function deleteUser(req, res) {
        res.send(await userController.deleteUser(req.params.id));
    }

    router.delete('/api/users/:id', auth.requireAdmin, asyncHandler(deleteUser));
    return router;
};
