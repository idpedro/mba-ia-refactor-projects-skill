"""Entry point: `python app.py` (ou `flask --app app run`). A montagem fica em src/app.py."""
from src.app import create_app
from src.config import Settings
from src.database import db

app = create_app()

__all__ = ["app", "db"]

if __name__ == "__main__":
    app.run(host=Settings.HOST, port=Settings.PORT, debug=Settings.DEBUG)
