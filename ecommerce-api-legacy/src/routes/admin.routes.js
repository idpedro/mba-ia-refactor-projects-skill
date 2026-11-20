const express = require('express');
const asyncHandler = require('../middlewares/asyncHandler');

module.exports = function adminRoutes({ reportController, auth }) {
    const router = express.Router();

    async function financialReport(req, res) {
        res.json(await reportController.financialReport());
    }

    router.get('/api/admin/financial-report', auth.requireAdmin, asyncHandler(financialReport));
    return router;
};
