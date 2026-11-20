const sqlite3 = require('sqlite3');

// Uma conexão única (o banco padrão é em memória) com API promisificada.
// Como a conexão é compartilhada, todo trabalho de um caso de uso passa por uma
// fila: transações nunca se intercalam e leituras não enxergam escritas ainda
// não confirmadas de outra requisição.
function createConnection(path) {
    const raw = new sqlite3.Database(path);
    let queue = Promise.resolve();

    const run = (sql, params = []) => new Promise((resolve, reject) => {
        raw.run(sql, params, function onRun(err) {
            if (err) return reject(err);
            return resolve({ lastID: this.lastID, changes: this.changes });
        });
    });

    const get = (sql, params = []) => new Promise((resolve, reject) => {
        raw.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
    });

    const all = (sql, params = []) => new Promise((resolve, reject) => {
        raw.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)));
    });

    const enqueue = (work) => {
        const result = queue.then(work);
        queue = result.catch(() => {});
        return result;
    };

    // Executa `work` sozinho na conexão, sem transação (leituras).
    const exclusive = (work) => enqueue(work);

    // Executa `work` sozinho na conexão, dentro de BEGIN/COMMIT; ROLLBACK em erro.
    const transaction = (work) => enqueue(async () => {
        await run('BEGIN IMMEDIATE');
        try {
            const value = await work();
            await run('COMMIT');
            return value;
        } catch (err) {
            await run('ROLLBACK').catch(() => {});
            throw err;
        }
    });

    const close = () => new Promise((resolve, reject) => {
        raw.close((err) => (err ? reject(err) : resolve()));
    });

    return { raw, run, get, all, exclusive, transaction, close };
}

module.exports = { createConnection };
