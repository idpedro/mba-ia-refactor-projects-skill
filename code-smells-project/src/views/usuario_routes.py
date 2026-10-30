from flask import Blueprint, jsonify, request

from src.middlewares.auth import issue_token, require_admin, require_self_or_admin


def build_usuario_routes(controller):
    bp = Blueprint("usuarios", __name__)

    @bp.get("/usuarios")
    @require_admin
    def listar_usuarios():
        return jsonify({"dados": controller.listar(), "sucesso": True}), 200

    @bp.get("/usuarios/<int:usuario_id>")
    @require_self_or_admin("usuario_id")
    def buscar_usuario(usuario_id):
        return jsonify({"dados": controller.obter(usuario_id), "sucesso": True}), 200

    @bp.post("/usuarios")
    def criar_usuario():
        usuario_id = controller.criar(request.get_json(silent=True))
        return jsonify({"dados": {"id": usuario_id}, "sucesso": True}), 201

    @bp.post("/login")
    def login():
        usuario = controller.login(request.get_json(silent=True))
        return jsonify({
            "dados": usuario,
            "token": issue_token(usuario["id"]),
            "sucesso": True,
            "mensagem": "Login OK",
        }), 200

    return bp
