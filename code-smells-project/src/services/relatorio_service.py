from src.models.pedido_model import STATUS_APROVADO, STATUS_CANCELADO, STATUS_PENDENTE

# (faturamento mínimo exclusivo, taxa de desconto), da maior faixa para a menor
FAIXAS_DESCONTO = ((10000, 0.10), (5000, 0.05), (1000, 0.02))


def calcular_desconto(faturamento):
    for minimo, taxa in FAIXAS_DESCONTO:
        if faturamento > minimo:
            return faturamento * taxa
    return 0


class RelatorioService:
    def __init__(self, pedido_model):
        self.pedidos = pedido_model

    def vendas(self):
        por_status = self.pedidos.totais_por_status()
        total_pedidos = sum(quantidade for quantidade, _ in por_status.values())
        faturamento = sum(soma for _, soma in por_status.values()) or 0
        desconto = calcular_desconto(faturamento)
        return {
            "total_pedidos": total_pedidos,
            "faturamento_bruto": round(faturamento, 2),
            "desconto_aplicavel": round(desconto, 2),
            "faturamento_liquido": round(faturamento - desconto, 2),
            "pedidos_pendentes": por_status.get(STATUS_PENDENTE, (0, 0))[0],
            "pedidos_aprovados": por_status.get(STATUS_APROVADO, (0, 0))[0],
            "pedidos_cancelados": por_status.get(STATUS_CANCELADO, (0, 0))[0],
            "ticket_medio": round(faturamento / total_pedidos, 2) if total_pedidos > 0 else 0,
        }
