from src.errors import ValidationError
from src.models.pedido_model import STATUS_VALIDOS

CATEGORIAS_VALIDAS = ["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]
CATEGORIA_PADRAO = "geral"
NOME_MIN = 2
NOME_MAX = 200


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def exigir_corpo(dados):
    if not dados or not isinstance(dados, dict):
        raise ValidationError("Dados inválidos")
    return dados


def validar_produto(dados):
    dados = exigir_corpo(dados)
    for campo, label in (("nome", "Nome"), ("preco", "Preço"), ("estoque", "Estoque")):
        if campo not in dados:
            raise ValidationError(f"{label} é obrigatório")

    nome = dados["nome"]
    descricao = dados.get("descricao", "")
    preco = dados["preco"]
    estoque = dados["estoque"]
    categoria = dados.get("categoria", CATEGORIA_PADRAO)

    if not isinstance(nome, str):
        raise ValidationError("Nome deve ser texto")
    if not isinstance(descricao, str):
        raise ValidationError("Descrição deve ser texto")
    if not _is_number(preco):
        raise ValidationError("Preço deve ser numérico")
    if not _is_int(estoque):
        raise ValidationError("Estoque deve ser inteiro")
    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")
    if len(nome) < NOME_MIN:
        raise ValidationError("Nome muito curto")
    if len(nome) > NOME_MAX:
        raise ValidationError("Nome muito longo")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError("Categoria inválida. Válidas: " + str(CATEGORIAS_VALIDAS))

    return {"nome": nome, "descricao": descricao, "preco": preco,
            "estoque": estoque, "categoria": categoria}


def validar_filtros_busca(args):
    def _preco(nome):
        valor = args.get(nome)
        if not valor:
            return None
        try:
            return float(valor)
        except ValueError:
            raise ValidationError(f"{nome} deve ser numérico") from None

    return {
        "termo": args.get("q", ""),
        "categoria": args.get("categoria"),
        "preco_min": _preco("preco_min"),
        "preco_max": _preco("preco_max"),
    }


def validar_usuario(dados):
    dados = exigir_corpo(dados)
    nome, email, senha = (dados.get(c, "") for c in ("nome", "email", "senha"))
    if not nome or not email or not senha:
        raise ValidationError("Nome, email e senha são obrigatórios")
    if not all(isinstance(v, str) for v in (nome, email, senha)):
        raise ValidationError("Nome, email e senha devem ser texto")
    return {"nome": nome, "email": email, "senha": senha}


def validar_login(dados):
    if not isinstance(dados, dict):
        dados = {}
    email, senha = dados.get("email", ""), dados.get("senha", "")
    if not email or not senha:
        raise ValidationError("Email e senha são obrigatórios")
    if not isinstance(email, str) or not isinstance(senha, str):
        raise ValidationError("Email e senha devem ser texto")
    return {"email": email, "senha": senha}


def validar_pedido(dados):
    dados = exigir_corpo(dados)
    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])
    if not usuario_id:
        raise ValidationError("Usuario ID é obrigatório")
    if not itens:
        raise ValidationError("Pedido deve ter pelo menos 1 item")
    if not isinstance(itens, list):
        raise ValidationError("Itens deve ser uma lista")
    for item in itens:
        if not isinstance(item, dict) or not _is_int(item.get("produto_id")) or not _is_int(item.get("quantidade")):
            raise ValidationError("Cada item precisa de produto_id e quantidade inteiros")
    return {"usuario_id": usuario_id, "itens": itens}


def validar_status(dados):
    novo_status = dados.get("status", "") if isinstance(dados, dict) else ""
    if novo_status not in STATUS_VALIDOS:
        raise ValidationError("Status inválido")
    return novo_status
