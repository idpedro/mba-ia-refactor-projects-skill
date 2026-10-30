import re

from src.errors import ValidationError

CATEGORIAS_VALIDAS = ("informatica", "moveis", "vestuario", "geral", "eletronicos", "livros")
CATEGORIA_PADRAO = "geral"
STATUS_VALIDOS = ("pendente", "aprovado", "enviado", "entregue", "cancelado")
NOME_MIN = 2
NOME_MAX = 200
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _exigir_dict(dados):
    if not isinstance(dados, dict) or not dados:
        raise ValidationError("Dados inválidos")


def _numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def _inteiro_positivo(valor):
    return isinstance(valor, int) and not isinstance(valor, bool) and valor > 0


def validar_produto(dados):
    _exigir_dict(dados)
    for campo, rotulo in (("nome", "Nome"), ("preco", "Preço"), ("estoque", "Estoque")):
        if campo not in dados:
            raise ValidationError(f"{rotulo} é obrigatório")

    nome = dados["nome"]
    descricao = dados.get("descricao", "")
    preco = dados["preco"]
    estoque = dados["estoque"]
    categoria = dados.get("categoria", CATEGORIA_PADRAO)

    if not _numero(preco):
        raise ValidationError("Preço deve ser numérico")
    if not isinstance(estoque, int) or isinstance(estoque, bool):
        raise ValidationError("Estoque deve ser inteiro")
    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")
    if not isinstance(nome, str) or len(nome) < NOME_MIN:
        raise ValidationError("Nome muito curto")
    if len(nome) > NOME_MAX:
        raise ValidationError("Nome muito longo")
    if not isinstance(descricao, str):
        raise ValidationError("Descrição deve ser texto")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError("Categoria inválida. Válidas: " + str(list(CATEGORIAS_VALIDAS)))

    return {"nome": nome, "descricao": descricao, "preco": preco, "estoque": estoque, "categoria": categoria}


def validar_filtros_busca(args):
    filtros = {"termo": args.get("q", ""), "categoria": args.get("categoria") or None}
    for campo in ("preco_min", "preco_max"):
        valor = args.get(campo)
        if valor:
            try:
                filtros[campo] = float(valor)
            except ValueError:
                raise ValidationError(f"{campo} deve ser numérico")
        else:
            filtros[campo] = None
    return filtros


def validar_usuario(dados):
    _exigir_dict(dados)
    nome = dados.get("nome", "")
    email = dados.get("email", "")
    senha = dados.get("senha", "")
    if not all(isinstance(v, str) and v for v in (nome, email, senha)):
        raise ValidationError("Nome, email e senha são obrigatórios")
    if not EMAIL_RE.match(email):
        raise ValidationError("Email inválido")
    return {"nome": nome, "email": email, "senha": senha}


def validar_login(dados):
    if not isinstance(dados, dict):
        raise ValidationError("Email e senha são obrigatórios")
    email = dados.get("email", "")
    senha = dados.get("senha", "")
    if not (isinstance(email, str) and email and isinstance(senha, str) and senha):
        raise ValidationError("Email e senha são obrigatórios")
    return email, senha


def validar_pedido(dados):
    _exigir_dict(dados)
    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])
    if not usuario_id:
        raise ValidationError("Usuario ID é obrigatório")
    if not _inteiro_positivo(usuario_id):
        raise ValidationError("Usuario ID inválido")
    if not itens or not isinstance(itens, list):
        raise ValidationError("Pedido deve ter pelo menos 1 item")
    for item in itens:
        if not (isinstance(item, dict)
                and _inteiro_positivo(item.get("produto_id"))
                and _inteiro_positivo(item.get("quantidade"))):
            raise ValidationError("Item inválido: produto_id e quantidade devem ser inteiros positivos")
    return {
        "usuario_id": usuario_id,
        "itens": [{"produto_id": i["produto_id"], "quantidade": i["quantidade"]} for i in itens],
    }


def validar_status(dados):
    status = dados.get("status", "") if isinstance(dados, dict) else ""
    if status not in STATUS_VALIDOS:
        raise ValidationError("Status inválido")
    return status


def validar_query(dados):
    sql = dados.get("sql", "") if isinstance(dados, dict) else ""
    if not isinstance(sql, str) or not sql.strip():
        raise ValidationError("Query não informada")
    sql = sql.strip().rstrip(";").strip()
    if ";" in sql or not sql.upper().startswith("SELECT"):
        raise ValidationError("Apenas uma instrução SELECT é permitida")
    return sql
