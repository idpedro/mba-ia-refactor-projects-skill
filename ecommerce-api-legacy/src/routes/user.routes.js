const express = require('express');
const asyncHandler = require('../middlewares/asyncHandler');

module.exports = function userRoutes(userController, adminAuth) {
    const router = express.Router();

    router.delete('/api/users/:id', adminAuth, asyncHandler(async (req, res) => {
        res.send(await userController.remove(req.params.id));
    }));

    return router;
};
