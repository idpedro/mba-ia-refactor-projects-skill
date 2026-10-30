const express = require('express');
const asyncHandler = require('../middlewares/asyncHandler');

module.exports = function adminRoutes(reportController, adminAuth) {
    const router = express.Router();

    router.get('/api/admin/financial-report', adminAuth, asyncHandler(async (req, res) => {
        res.json(await reportController.financialReport());
    }));

    return router;
};
