// Express 4 does not forward rejected promises; route them to the error handler.
module.exports = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);
