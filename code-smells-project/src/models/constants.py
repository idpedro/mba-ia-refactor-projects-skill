"""Regras de domínio nomeadas (limites, listas válidas, faixas comerciais)."""

NOME_MIN = 2
NOME_MAX = 200

CATEGORIA_PADRAO = "geral"
CATEGORIAS_VALIDAS = ("informatica", "moveis", "vestuario", "geral", "eletronicos", "livros")

STATUS_PENDENTE = "pendente"
STATUS_APROVADO = "aprovado"
STATUS_ENVIADO = "enviado"
STATUS_ENTREGUE = "entregue"
STATUS_CANCELADO = "cancelado"
STATUS_PEDIDO = (STATUS_PENDENTE, STATUS_APROVADO, STATUS_ENVIADO, STATUS_ENTREGUE, STATUS_CANCELADO)

TIPO_ADMIN = "admin"
TIPO_CLIENTE = "cliente"

# (faturamento mínimo exclusivo, taxa), da maior faixa para a menor
FAIXAS_DESCONTO = ((10000, 0.10), (5000, 0.05), (1000, 0.02))
