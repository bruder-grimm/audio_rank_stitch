from app_state import AppState
from audio.telephone_record import Recorder
from flask import Flask, render_template, jsonify, request


class RecordingFrontend:
    """Web-based frontend for recording display."""
    
    def __init__(
            self, 
            recorder: Recorder, 
            app_state: AppState,
            port: int = 5001, 
            host: str = "127.0.0.1", 
        ):
        self.host = host
        self.port = port
        self.recorder = recorder
        self.app = Flask(__name__,
                        template_folder="recording_templates",
                        static_folder="recording_static")
        
        # State
        self._app_state = app_state
        self._background_color = "#ffffff"
        self._text_color = "#000000"
        self._is_recording = False
        
        # Register routes
        self.app.route("/")(self._index)
        self.app.route("/api/status", methods=["GET"])(self._get_status)
        self.app.route("/api/colors", methods=["GET"])(self._get_colors)
        self.app.route("/api/spacebar", methods=["POST"])(self._handle_spacebar)

    def set_background_color(self, color: str):
        """Set the background color for the frontend."""
        self._background_color = color

    def _index(self):
        """Serve main HTML page."""
        return render_template("index.html")
    
    def _get_status(self):
        """Get current instruction text."""
        return jsonify({
            "instruction": self._app_state.get_current_instruction(),
            "background_color": self._background_color,
        })
    
    def _get_colors(self):
        """Get current colors."""
        return jsonify({
            "background_color": self._background_color,
        })
    
    def _handle_spacebar(self):
        """
        Handle spacebar press/release events. This holds all the logic for playing the last recording,
        beeping, priming the recorder. Maybe this should also have timers for the prompt logic etc?
        """
        if not self.recorder:
            return jsonify({"status": "no_recorder"}), 400
        
        data = request.json
        event_type = data.get("type")  # "down" or "up"
        
        if event_type == "down":
            self._app_state.phone_picked_up.set()
        elif event_type == "up":
            self._app_state.phone_picked_up.clear()
        
        return jsonify({"status": "ok"})
    
    def run(self, debug: bool = False):
        """Start the Flask server."""
        self.app.run(host=self.host, port=self.port, debug=debug, use_reloader=False)