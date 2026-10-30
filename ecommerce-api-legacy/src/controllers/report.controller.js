class ReportController {
    constructor({ reportService }) {
        this.reportService = reportService;
    }

    financialReport() {
        return this.reportService.financialReport();
    }
}

module.exports = ReportController;
