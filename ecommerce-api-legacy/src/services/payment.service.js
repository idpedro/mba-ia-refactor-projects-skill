const PAYMENT_STATUS = Object.freeze({ PAID: 'PAID', DENIED: 'DENIED' });

// Simulated gateway rule: cards starting with this prefix are approved.
const APPROVED_CARD_PREFIX = '4';
const VISIBLE_CARD_DIGITS = 4;

class PaymentService {
    constructor({ gatewayKey, logger }) {
        this.gatewayKey = gatewayKey;
        this.logger = logger;
    }

    charge(card, amount) {
        const masked = card.length > VISIBLE_CARD_DIGITS ? card.slice(-VISIBLE_CARD_DIGITS) : '****';
        this.logger.info(`Processing card ending ${masked} amount=${amount}`);
        return card.startsWith(APPROVED_CARD_PREFIX) ? PAYMENT_STATUS.PAID : PAYMENT_STATUS.DENIED;
    }
}

module.exports = { PaymentService, PAYMENT_STATUS };
