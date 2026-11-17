const express = require('express');
const asyncHandler = require('../middlewares/asyncHandler');

function userRoutes(userController, adminAuth) {
    const router = express.Router();

    router.delete('/api/users/:id', adminAuth, asyncHandler(async (req, res) => {
        res.send(await userController.deleteUser(req.params.id));
    }));

    return router;
}

module.exports = userRoutes;
