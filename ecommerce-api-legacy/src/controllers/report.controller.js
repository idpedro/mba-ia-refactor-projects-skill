class ReportController {
    constructor({ reportService }) {
        this.reports = reportService;
    }

    financialReport() {
        return this.reports.financialReport();
    }
}

module.exports = ReportController;
