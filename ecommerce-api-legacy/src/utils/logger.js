// Único ponto da aplicação que escreve no console.
function write(stream, level, message) {
    stream(`${new Date().toISOString()} ${level} ${message}`);
}

module.exports = {
    info: (message) => write(console.log, 'INFO', message),
    warn: (message) => write(console.warn, 'WARN', message),
    error: (message, err) => write(console.error, 'ERROR', err ? `${message}\n${err.stack || err}` : message),
};
