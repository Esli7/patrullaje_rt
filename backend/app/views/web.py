from flask import Blueprint

# Blueprint “web” simple para que la app arranque
web_bp = Blueprint("web", __name__)

@web_bp.route("/")
def home():
    return "OK - web blueprint up"
