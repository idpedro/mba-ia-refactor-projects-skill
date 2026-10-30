class CacheService {
    constructor(logger) {
        this.store = new Map();
        this.logger = logger;
    }

    set(key, value) {
        this.logger.debug(`Salvando no cache: ${key}`);
        this.store.set(key, value);
    }

    get(key) {
        return this.store.get(key);
    }
}

module.exports = CacheService;
