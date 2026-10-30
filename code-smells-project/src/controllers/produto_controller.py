import logging

from src.controllers.validators import validar_filtros_busca, validar_produto
from src.errors import ConflictError, NotFoundError

logger = logging.getLogger(__name__)


class ProdutoController:
    def __init__(self, produto_model, pedido_model):
        self.produtos = produto_model
        self.pedidos = pedido_model

    def listar(self):
        return self.produtos.listar()

    def buscar(self, args):
        return self.produtos.buscar(**validar_filtros_busca(args))

    def obter(self, produto_id):
        produto = self.produtos.buscar_por_id(produto_id)
        if produto is None:
            raise NotFoundError("Produto não encontrado")
        return produto

    def criar(self, dados):
        produto = validar_produto(dados)
        produto_id = self.produtos.criar(**produto)
        logger.info("Produto criado id=%s", produto_id)
        return produto_id

    def atualizar(self, produto_id, dados):
        self.obter(produto_id)
        self.produtos.atualizar(produto_id, **validar_produto(dados))

    def deletar(self, produto_id):
        self.obter(produto_id)
        if self.pedidos.produto_tem_itens(produto_id):
            raise ConflictError("Produto possui pedidos vinculados")
        self.produtos.deletar(produto_id)
        logger.info("Produto deletado id=%s", produto_id)
