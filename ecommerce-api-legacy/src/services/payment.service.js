const PAYMENT_STATUS = Object.freeze({ PAID: 'PAID', DENIED: 'DENIED' });

// Simulated gateway: cards starting with "4" are approved.
const APPROVED_CARD_PREFIX = '4';
const VISIBLE_CARD_DIGITS = 4;

class PaymentService {
    constructor({ gatewayKey, logger }) {
        this.gatewayKey = gatewayKey;
        this.logger = logger;
    }

    // Returns PAID or DENIED. Never logs the full card number or the gateway key.
    charge(card) {
        this.logger.info(
            `Processando cartão final ${card.slice(-VISIBLE_CARD_DIGITS)} (gateway ${this.gatewayKey ? 'configurado' : 'não configurado'})`);
        return card.startsWith(APPROVED_CARD_PREFIX) ? PAYMENT_STATUS.PAID : PAYMENT_STATUS.DENIED;
    }
}

module.exports = { PaymentService, PAYMENT_STATUS };
