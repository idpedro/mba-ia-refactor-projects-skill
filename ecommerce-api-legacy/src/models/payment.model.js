class PaymentModel {
    constructor(db) {
        this.db = db;
    }

    async create({ enrollmentId, amount, status }, executor = this.db) {
        const { lastID } = await executor.run(
            'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
            [enrollmentId, amount, status]);
        return lastID;
    }

    // One row per (course, enrollment) with the student and payment attached.
    // A course with no enrollment comes back once with null enrollment fields.
    findCourseEnrollmentRows() {
        return this.db.all(
            `SELECT c.id AS course_id, c.title AS course_title,
                    e.id AS enrollment_id,
                    u.name AS student_name,
                    p.amount AS payment_amount, p.status AS payment_status
               FROM courses c
               LEFT JOIN enrollments e ON e.course_id = c.id
               LEFT JOIN users u ON u.id = e.user_id
               LEFT JOIN payments p ON p.enrollment_id = e.id
              ORDER BY c.id, e.id`);
    }
}

module.exports = PaymentModel;
