"""Entrypoint: `python app.py` sobe a app criada pela composition root em src/app.py."""
from src.app import create_app
from src.config.settings import Settings

app = create_app()

if __name__ == "__main__":
    app.run(host=Settings.HOST, port=Settings.PORT, debug=Settings.DEBUG)
