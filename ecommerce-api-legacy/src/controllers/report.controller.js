class ReportController {
    constructor({ db, reportService }) {
        this.db = db;
        this.reportService = reportService;
    }

    financialReport() {
        return this.db.exclusive(() => this.reportService.financialReport());
    }
}

module.exports = { ReportController };
