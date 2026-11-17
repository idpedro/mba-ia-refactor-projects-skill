from src.errors import ValidationError
from src.models.pedido_model import STATUS_PEDIDO
from src.models.produto_model import CATEGORIAS_VALIDAS

NOME_MIN, NOME_MAX = 2, 200


def _corpo(dados):
    if not isinstance(dados, dict) or not dados:
        raise ValidationError("Dados inválidos")
    return dados


def _numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def _inteiro(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)


def validar_produto(dados):
    dados = _corpo(dados)
    for campo, rotulo in (("nome", "Nome"), ("preco", "Preço"), ("estoque", "Estoque")):
        if campo not in dados:
            raise ValidationError(f"{rotulo} é obrigatório")
    nome, descricao = dados["nome"], dados.get("descricao", "")
    preco, estoque = dados["preco"], dados["estoque"]
    categoria = dados.get("categoria", "geral")

    if not _numero(preco) or preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if not _numero(estoque) or estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")
    if not isinstance(nome, str) or len(nome) < NOME_MIN:
        raise ValidationError("Nome muito curto")
    if len(nome) > NOME_MAX:
        raise ValidationError("Nome muito longo")
    if not isinstance(descricao, str):
        raise ValidationError("Descrição inválida")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError("Categoria inválida. Válidas: " + str(list(CATEGORIAS_VALIDAS)))
    return {"nome": nome, "descricao": descricao, "preco": preco, "estoque": estoque, "categoria": categoria}


def validar_busca(args):
    filtros = {"termo": args.get("q", ""), "categoria": args.get("categoria")}
    for chave in ("preco_min", "preco_max"):
        bruto = args.get(chave)
        try:
            filtros[chave] = float(bruto) if bruto else None
        except ValueError:
            raise ValidationError(f"{chave} deve ser numérico")
    return filtros


def validar_usuario(dados):
    dados = _corpo(dados)
    nome, email, senha = dados.get("nome", ""), dados.get("email", ""), dados.get("senha", "")
    if not nome or not email or not senha:
        raise ValidationError("Nome, email e senha são obrigatórios")
    if not all(isinstance(v, str) for v in (nome, email, senha)):
        raise ValidationError("Nome, email e senha devem ser texto")
    return {"nome": nome, "email": email, "senha": senha}


def validar_login(dados):
    if not isinstance(dados, dict):
        raise ValidationError("Dados inválidos")
    email, senha = dados.get("email", ""), dados.get("senha", "")
    if not email or not senha:
        raise ValidationError("Email e senha são obrigatórios")
    if not isinstance(email, str) or not isinstance(senha, str):
        raise ValidationError("Email e senha devem ser texto")
    return {"email": email, "senha": senha}


def validar_pedido(dados):
    dados = _corpo(dados)
    usuario_id, itens = dados.get("usuario_id"), dados.get("itens", [])
    if not usuario_id:
        raise ValidationError("Usuario ID é obrigatório")
    if not _inteiro(usuario_id):
        raise ValidationError("Usuario ID inválido")
    if not itens:
        raise ValidationError("Pedido deve ter pelo menos 1 item")
    if not isinstance(itens, list):
        raise ValidationError("Itens inválidos")
    for item in itens:
        if not isinstance(item, dict) or not _inteiro(item.get("produto_id")):
            raise ValidationError("Cada item precisa de produto_id inteiro")
        if not _inteiro(item.get("quantidade")) or item["quantidade"] <= 0:
            raise ValidationError("Quantidade deve ser um inteiro positivo")
    return {"usuario_id": usuario_id, "itens": itens}


def validar_status(dados):
    if not isinstance(dados, dict):
        raise ValidationError("Dados inválidos")
    status = dados.get("status", "")
    if status not in STATUS_PEDIDO:
        raise ValidationError("Status inválido")
    return status


def validar_consulta(dados):
    if not isinstance(dados, dict) or not dados.get("sql"):
        raise ValidationError("Query não informada")
    if not isinstance(dados["sql"], str):
        raise ValidationError("Query inválida")
    return dados["sql"]
