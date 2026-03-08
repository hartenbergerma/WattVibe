from flask import Flask, jsonify, render_template

from .control_status import get_status

def run_web_server(port: int = 5001):
    app = Flask(__name__)

    @app.route("/")
    def index():
        # Flask sucht automatisch im Ordner "templates" nach index.html
        return render_template("index.html")

    @app.route("/status")
    def status():
        return jsonify(get_status())

    app.run(host="0.0.0.0", port=port)