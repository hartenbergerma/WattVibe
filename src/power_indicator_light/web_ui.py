import threading
import logging
from flask import Flask, jsonify, render_template
from werkzeug.serving import make_server
from .control_status import get_status

class WebServer(threading.Thread):
    def __init__(self, port: int = 5001):
        super().__init__(name="WebServerThread")
        self.port = port
        self.app = Flask(__name__)

        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        
        # Routen registrieren
        self._setup_routes()
        
        # Server-Instanz vorbereiten (noch nicht gestartet)
        self.server = make_server("0.0.0.0", self.port, self.app)
        self.ctx = self.app.app_context()
        self.ctx.push()

    def _setup_routes(self):
        @self.app.route("/")
        def index():
            return render_template("index.html")

        @self.app.route("/status")
        def status():
            return jsonify(get_status())

    def run(self):
        """Wird aufgerufen, wenn thread.start() ausgeführt wird."""
        print(f"Webserver startet auf Port {self.port}...")
        self.server.serve_forever()

    def shutdown(self):
        """Beendet den Webserver sauber von außen."""
        print("Webserver wird beendet...")
        self.server.shutdown()