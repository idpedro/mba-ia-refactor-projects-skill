STATUS_PENDENTE = "pendente"
STATUS_APROVADO = "aprovado"
STATUS_CANCELADO = "cancelado"

# (faturamento mínimo exclusivo, taxa de desconto), da maior faixa para a menor.
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
        resumo = self.pedidos.resumo_por_status()
        total_pedidos = sum(quantidade for quantidade, _ in resumo.values())
        faturamento = sum(valor for _, valor in resumo.values())
        desconto = calcular_desconto(faturamento)

        def contagem(status):
            return resumo.get(status, (0, 0))[0]

        return {
            "total_pedidos": total_pedidos,
            "faturamento_bruto": round(faturamento, 2),
            "desconto_aplicavel": round(desconto, 2),
            "faturamento_liquido": round(faturamento - desconto, 2),
            "pedidos_pendentes": contagem(STATUS_PENDENTE),
            "pedidos_aprovados": contagem(STATUS_APROVADO),
            "pedidos_cancelados": contagem(STATUS_CANCELADO),
            "ticket_medio": round(faturamento / total_pedidos, 2) if total_pedidos > 0 else 0,
        }
