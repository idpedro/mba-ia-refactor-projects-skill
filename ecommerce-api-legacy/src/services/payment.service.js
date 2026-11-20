const PAYMENT_STATUS = Object.freeze({ PAID: 'PAID', DENIED: 'DENIED' });

// Gateway simulado: cartões com este prefixo são aprovados.
const APPROVED_CARD_PREFIX = '4';
const VISIBLE_CARD_DIGITS = 4;

class PaymentService {
    constructor({ logger }) {
        this.logger = logger;
    }

    charge(card, amount) {
        this.logger.info(`Processando cartão final ${card.slice(-VISIBLE_CARD_DIGITS)} no valor de ${amount}`);
        return card.startsWith(APPROVED_CARD_PREFIX) ? PAYMENT_STATUS.PAID : PAYMENT_STATUS.DENIED;
    }
}

module.exports = { PaymentService, PAYMENT_STATUS };
