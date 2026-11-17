const LEVELS = { debug: 10, info: 20, warn: 30, error: 40 };

// Tiny leveled logger over console; no logging dependency needed.
function createLogger(level = 'info') {
    const threshold = LEVELS[level] || LEVELS.info;

    const write = (name, message, extra) => {
        if (LEVELS[name] < threshold) return;
        const line = `${new Date().toISOString()} ${name.toUpperCase()} ${message}`;
        const sink = name === 'error' || name === 'warn' ? console.error : console.log;
        if (extra === undefined) sink(line);
        else sink(line, extra);
    };

    return {
        debug: (message, extra) => write('debug', message, extra),
        info: (message, extra) => write('info', message, extra),
        warn: (message, extra) => write('warn', message, extra),
        error: (message, extra) => write('error', message, extra),
    };
}

module.exports = { createLogger };
