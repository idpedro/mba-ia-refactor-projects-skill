class AuditLogModel {
    constructor(db) {
        this.db = db;
    }

    record(action, executor = this.db) {
        return executor.run(
            "INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))", [action]);
    }
}

module.exports = AuditLogModel;
