const express = require('express');
const asyncHandler = require('../middlewares/asyncHandler');

module.exports = (userController, adminAuth) => {
    const router = express.Router();

    router.delete('/api/users/:id', adminAuth, asyncHandler(async (req, res) => {
        await userController.delete(req.params.id);
        res.send('Usuário deletado.');
    }));

    return router;
};
