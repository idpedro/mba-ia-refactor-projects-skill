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

    def buscar(self, produto_id):
        produto = self.produtos.buscar_por_id(produto_id)
        if not produto:
            raise NotFoundError("Produto não encontrado")
        return produto

    def pesquisar(self, args):
        filtros = validar_filtros_busca(args)
        return self.produtos.buscar(**filtros)

    def criar(self, dados):
        produto = validar_produto(dados)
        produto_id = self.produtos.criar(**produto)
        logger.info("Produto criado id=%s", produto_id)
        return produto_id

    def atualizar(self, produto_id, dados):
        self.buscar(produto_id)
        produto = validar_produto(dados)
        self.produtos.atualizar(produto_id, **produto)

    def deletar(self, produto_id):
        self.buscar(produto_id)
        self.produtos.deletar(produto_id)
        logger.info("Produto deletado id=%s", produto_id)
