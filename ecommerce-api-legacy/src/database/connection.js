const sqlite3 = require('sqlite3');

const promisifyRun = (db, sql, params) => new Promise((resolve, reject) =>
    db.run(sql, params, function onRun(err) {
        if (err) reject(err);
        else resolve({ lastID: this.lastID, changes: this.changes });
    }));

const promisifyGet = (db, sql, params) => new Promise((resolve, reject) =>
    db.get(sql, params, (err, row) => (err ? reject(err) : resolve(row))));

const promisifyAll = (db, sql, params) => new Promise((resolve, reject) =>
    db.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows))));

// One sqlite connection, promisified. Transactions are serialized through a
// lock: a single connection cannot hold two BEGIN at once.
function createConnection(dbPath) {
    const db = new sqlite3.Database(dbPath);

    const executor = {
        run: (sql, params = []) => promisifyRun(db, sql, params),
        get: (sql, params = []) => promisifyGet(db, sql, params),
        all: (sql, params = []) => promisifyAll(db, sql, params),
    };

    let lock = Promise.resolve();

    // `work` receives the executor to use inside the transaction.
    const transaction = (work) => {
        const result = lock.then(async () => {
            await executor.run('BEGIN');
            try {
                const value = await work(executor);
                await executor.run('COMMIT');
                return value;
            } catch (err) {
                await executor.run('ROLLBACK');
                throw err;
            }
        });
        lock = result.catch(() => {});
        return result;
    };

    const close = () => new Promise((resolve, reject) =>
        db.close((err) => (err ? reject(err) : resolve())));

    return { ...executor, transaction, close };
}

module.exports = { createConnection };
