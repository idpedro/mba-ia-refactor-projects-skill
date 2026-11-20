// Express 4 não encaminha promessas rejeitadas ao error handler sozinho.
module.exports = function asyncHandler(handler) {
    return function wrapped(req, res, next) {
        Promise.resolve(handler(req, res, next)).catch(next);
    };
};
