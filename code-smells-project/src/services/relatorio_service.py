FAIXAS_DESCONTO = ((10000, 0.10), (5000, 0.05), (1000, 0.02))  # (faturamento mínimo, taxa)


def calcular_desconto(faturamento):
    for minimo, taxa in FAIXAS_DESCONTO:
        if faturamento > minimo:
            return faturamento * taxa
    return 0


class RelatorioService:
    def __init__(self, sistema_model):
        self.sistema = sistema_model

    def vendas(self):
        resumo = self.sistema.resumo_pedidos()
        total_pedidos = sum(qtd for qtd, _ in resumo.values())
        faturamento = sum(valor for _, valor in resumo.values())
        desconto = calcular_desconto(faturamento)
        return {
            "total_pedidos": total_pedidos,
            "faturamento_bruto": round(faturamento, 2),
            "desconto_aplicavel": round(desconto, 2),
            "faturamento_liquido": round(faturamento - desconto, 2),
            "pedidos_pendentes": resumo.get("pendente", (0, 0))[0],
            "pedidos_aprovados": resumo.get("aprovado", (0, 0))[0],
            "pedidos_cancelados": resumo.get("cancelado", (0, 0))[0],
            "ticket_medio": round(faturamento / total_pedidos, 2) if total_pedidos > 0 else 0,
        }
