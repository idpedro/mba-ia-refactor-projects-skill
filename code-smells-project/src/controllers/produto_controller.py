import logging

from src.controllers.validators import validar_filtros_busca, validar_produto
from src.errors import NotFoundError

logger = logging.getLogger(__name__)


class ProdutoController:
    def __init__(self, produto_model):
        self.produtos = produto_model

    def listar(self):
        produtos = self.produtos.listar()
        logger.debug("Listando %s produtos", len(produtos))
        return produtos

    def buscar(self, args):
        filtros = validar_filtros_busca(args)
        return self.produtos.buscar(**filtros)

    def obter(self, produto_id):
        produto = self.produtos.buscar_por_id(produto_id)
        if produto is None:
            raise NotFoundError("Produto não encontrado")
        return produto

    def criar(self, dados):
        produto_id = self.produtos.criar(validar_produto(dados))
        logger.info("Produto criado id=%s", produto_id)
        return produto_id

    def atualizar(self, produto_id, dados):
        self.obter(produto_id)
        self.produtos.atualizar(produto_id, validar_produto(dados))
        logger.info("Produto atualizado id=%s", produto_id)

    def remover(self, produto_id):
        self.obter(produto_id)
        self.produtos.desativar(produto_id)
        logger.info("Produto desativado id=%s", produto_id)
