const express = require('express');
const asyncHandler = require('../middlewares/asyncHandler');

module.exports = function checkoutRoutes({ checkoutController, auth }) {
    const router = express.Router();

    async function checkout(req, res) {
        res.status(200).json(await checkoutController.checkout(req.body, req.user || null));
    }

    router.post('/api/checkout', auth.optionalAuth, asyncHandler(checkout));
    return router;
};
