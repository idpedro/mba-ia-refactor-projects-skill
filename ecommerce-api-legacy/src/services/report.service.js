const { PAYMENT_STATUS } = require('./payment.service');

class ReportService {
    constructor({ courseModel }) {
        this.courseModel = courseModel;
    }

    // Revenue counts PAID payments only; each student lists the amount of their payment, if any.
    async financialReport() {
        const rows = await this.courseModel.findAllWithEnrollments();
        const report = new Map();

        for (const row of rows) {
            if (!report.has(row.course_id)) {
                report.set(row.course_id, { course: row.course_title, revenue: 0, students: [] });
            }
            if (row.enrollment_id === null) continue;

            const courseData = report.get(row.course_id);
            const hasPayment = row.payment_amount !== null;
            if (hasPayment && row.payment_status === PAYMENT_STATUS.PAID) {
                courseData.revenue += row.payment_amount;
            }
            courseData.students.push({
                student: row.student_name ?? 'Unknown',
                paid: hasPayment ? row.payment_amount : 0,
            });
        }

        return [...report.values()];
    }
}

module.exports = ReportService;
