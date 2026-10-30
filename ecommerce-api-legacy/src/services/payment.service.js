const PAYMENT_STATUS = Object.freeze({ PAID: 'PAID', DENIED: 'DENIED' });

// Simulated gateway: cards starting with this prefix are approved.
const APPROVED_CARD_PREFIX = '4';

class PaymentService {
    constructor({ gatewayKey, logger }) {
        this.gatewayKey = gatewayKey;
        this.logger = logger;
    }

    charge(card, amount) {
        this.logger.info(`Processando cartão final ${card.slice(-4)} valor ${amount}`);
        return card.startsWith(APPROVED_CARD_PREFIX) ? PAYMENT_STATUS.PAID : PAYMENT_STATUS.DENIED;
    }
}

module.exports = { PaymentService, PAYMENT_STATUS, APPROVED_CARD_PREFIX };
