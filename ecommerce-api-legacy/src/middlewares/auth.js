const { verifyPassword } = require('../services/password.service');
const { ROLE_ADMIN } = require('../constants/roles');
const { UnauthorizedError, ForbiddenError } = require('../errors');

// HTTP Basic (email:senha) verificado contra os hashes armazenados.
function parseBasic(header) {
    const match = /^Basic\s+(\S+)$/i.exec(header || '');
    if (!match) return null;
    const decoded = Buffer.from(atob(match[1]), 'latin1').toString('utf8');
    const separator = decoded.indexOf(':');
    if (separator < 0) return null;
    return { email: decoded.slice(0, separator).trim().toLowerCase(), password: decoded.slice(separator + 1) };
}

function createAuth({ db, userModel }) {
    async function authenticate(req) {
        const header = req.get('Authorization');
        if (!header) return null;
        let credentials = null;
        try {
            credentials = parseBasic(header);
        } catch {
            credentials = null;
        }
        if (!credentials) throw new UnauthorizedError('Credenciais inválidas');

        const user = await db.exclusive(() => userModel.findByEmail(credentials.email));
        if (!user || !(await verifyPassword(credentials.password, user.pass))) {
            throw new UnauthorizedError('Credenciais inválidas');
        }
        return { id: user.id, email: user.email, role: user.role };
    }

    // Credencial opcional; se enviada, precisa ser válida.
    function optionalAuth(req, res, next) {
        authenticate(req).then((user) => { req.user = user; next(); }, next);
    }

    function requireAdmin(req, res, next) {
        authenticate(req).then((user) => {
            if (!user) {
                res.set('WWW-Authenticate', 'Basic realm="lms"');
                return next(new UnauthorizedError('Não autenticado'));
            }
            if (user.role !== ROLE_ADMIN) return next(new ForbiddenError('Acesso restrito a administradores'));
            req.user = user;
            return next();
        }, next);
    }

    return { optionalAuth, requireAdmin };
}

module.exports = { createAuth };
