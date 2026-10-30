const sqlite3 = require('sqlite3');

// Promise wrapper over a single sqlite3 connection. Every model shares this instance,
// which matters for ':memory:' databases (each connection is a separate database).
class Database {
    constructor(path) {
        this.db = new sqlite3.Database(path);
        this.queue = Promise.resolve();
    }

    run(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.db.run(sql, params, function (err) {
                if (err) return reject(err);
                resolve({ lastID: this.lastID, changes: this.changes });
            });
        });
    }

    get(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.db.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
        });
    }

    all(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.db.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)));
        });
    }

    exec(sql) {
        return new Promise((resolve, reject) => {
            this.db.exec(sql, (err) => (err ? reject(err) : resolve()));
        });
    }

    // Transactions are queued so two requests never interleave BEGIN/COMMIT on the shared connection.
    transaction(work) {
        const result = this.queue.then(async () => {
            await this.run('BEGIN');
            try {
                const value = await work();
                await this.run('COMMIT');
                return value;
            } catch (err) {
                await this.run('ROLLBACK');
                throw err;
            }
        });
        this.queue = result.catch(() => {});
        return result;
    }

    close() {
        return new Promise((resolve, reject) => this.db.close((err) => (err ? reject(err) : resolve())));
    }
}

function createConnection(path) {
    return new Database(path);
}

module.exports = { Database, createConnection };
