const sqlite3 = require('sqlite3');

// Promisified wrapper around one sqlite3.Database instance.
// Every query goes through the same connection (required for ':memory:').
class Database {
    constructor(filename) {
        this.db = new sqlite3.Database(filename);
        this.txQueue = Promise.resolve();
    }

    run(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.db.run(sql, params, function onRun(err) {
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

    // Transactions are serialized: a single connection cannot nest BEGIN.
    transaction(work) {
        const execute = async () => {
            await this.run('BEGIN');
            try {
                const result = await work();
                await this.run('COMMIT');
                return result;
            } catch (err) {
                await this.run('ROLLBACK');
                throw err;
            }
        };
        const result = this.txQueue.then(execute, execute);
        this.txQueue = result.catch(() => {});
        return result;
    }

    close() {
        return new Promise((resolve, reject) => this.db.close((err) => (err ? reject(err) : resolve())));
    }
}

function createConnection(filename) {
    return new Database(filename);
}

module.exports = { createConnection, Database };
