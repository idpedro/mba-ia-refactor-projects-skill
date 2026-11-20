"""Validação única de entrada por entidade. Mensagens originais preservadas."""
import math
import re

from src.errors import ValidationError
from src.models.constants import CATEGORIA_PADRAO, CATEGORIAS_VALIDAS, NOME_MAX, NOME_MIN, STATUS_PEDIDO

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

CAMPOS_PRODUTO = (
    ("nome", "Nome é obrigatório"),
    ("preco", "Preço é obrigatório"),
    ("estoque", "Estoque é obrigatório"),
)


def _numero_finito(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool) and math.isfinite(valor)


def _inteiro(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)


def validar_produto(dados):
    if not isinstance(dados, dict) or not dados:
        raise ValidationError("Dados inválidos")
    for campo, mensagem in CAMPOS_PRODUTO:
        if campo not in dados:
            raise ValidationError(mensagem)

    nome = dados["nome"]
    preco = dados["preco"]
    estoque = dados["estoque"]
    descricao = dados.get("descricao") or ""
    categoria = dados.get("categoria", CATEGORIA_PADRAO)

    if not isinstance(nome, str):
        raise ValidationError("Nome inválido")
    if not _numero_finito(preco):
        raise ValidationError("Preço deve ser um número")
    if not _inteiro(estoque):
        raise ValidationError("Estoque deve ser um número inteiro")
    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")
    if len(nome) < NOME_MIN:
        raise ValidationError("Nome muito curto")
    if len(nome) > NOME_MAX:
        raise ValidationError("Nome muito longo")
    if not isinstance(descricao, str):
        raise ValidationError("Descrição inválida")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError("Categoria inválida. Válidas: " + str(list(CATEGORIAS_VALIDAS)))

    return {"nome": nome, "descricao": descricao, "preco": preco, "estoque": estoque, "categoria": categoria}


def validar_filtros_busca(args):
    filtros = {"termo": args.get("q", ""), "categoria": args.get("categoria") or None}
    for campo in ("preco_min", "preco_max"):
        bruto = args.get(campo)
        if not bruto:
            filtros[campo] = None
            continue
        try:
            valor = float(bruto)
        except ValueError:
            raise ValidationError(f"{campo} inválido") from None
        if not math.isfinite(valor):
            raise ValidationError(f"{campo} inválido")
        filtros[campo] = valor
    return filtros


def validar_usuario(dados):
    if not isinstance(dados, dict) or not dados:
        raise ValidationError("Dados inválidos")
    nome, email, senha = (dados.get("nome", ""), dados.get("email", ""), dados.get("senha", ""))
    if not all(isinstance(valor, str) and valor for valor in (nome, email, senha)):
        raise ValidationError("Nome, email e senha são obrigatórios")
    if not EMAIL_RE.match(email):
        raise ValidationError("Email inválido")
    return {"nome": nome, "email": email, "senha": senha}


def validar_login(dados):
    dados = dados if isinstance(dados, dict) else {}
    email, senha = dados.get("email", ""), dados.get("senha", "")
    if not (isinstance(email, str) and email and isinstance(senha, str) and senha):
        raise ValidationError("Email e senha são obrigatórios")
    return email, senha


def validar_pedido(dados):
    if not isinstance(dados, dict) or not dados:
        raise ValidationError("Dados inválidos")
    usuario_id = dados.get("usuario_id")
    if usuario_id is not None and not (_inteiro(usuario_id) and usuario_id > 0):
        raise ValidationError("Usuario ID inválido")
    itens = dados.get("itens")
    if not itens:
        raise ValidationError("Pedido deve ter pelo menos 1 item")
    if not isinstance(itens, list):
        raise ValidationError("Itens inválidos")

    quantidades = {}
    for item in itens:
        produto_id = item.get("produto_id") if isinstance(item, dict) else None
        quantidade = item.get("quantidade") if isinstance(item, dict) else None
        if not (_inteiro(produto_id) and produto_id > 0 and _inteiro(quantidade) and quantidade >= 1):
            raise ValidationError("Item inválido: produto_id e quantidade devem ser inteiros positivos")
        quantidades[produto_id] = quantidades.get(produto_id, 0) + quantidade
    return {"usuario_id": usuario_id, "quantidades": quantidades}


def validar_status(dados):
    status = dados.get("status") if isinstance(dados, dict) else None
    if status not in STATUS_PEDIDO:
        raise ValidationError("Status inválido")
    return status
