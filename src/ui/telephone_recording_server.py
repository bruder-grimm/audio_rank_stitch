from app_state import AppState
from audio.telephone_record import Recorder
from flask import Flask, render_template, jsonify, request
from typing import Optional


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
    
    def _index(self):
        """Serve main HTML page."""
        return render_template("index.html")
    
    def _get_status(self):
        """Get current instruction text."""
        return jsonify({
            "instruction": self._app_state.instruction,
            "background_color": self._app_state.background_color,
            "text_color": self._app_state.text_color,
        })
    
    def _get_colors(self):
        """Get current colors."""
        return jsonify({
            "background_color": self._background_color,
            "text_color": self._text_color,
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
            if not self._is_recording:
                self._app_state.is_recording = True
                self.recorder.start()
                self._background_color = "#ce0000"  # Turn red
        elif event_type == "up":
            if self._is_recording:
                self.recorder.stop()
                self._app_state.is_recording = False
                self._background_color = "#ffffff"  # Turn white
        
        return jsonify({"status": "ok"})
    
    def run(self, debug: bool = False):
        """Start the Flask server."""
        self.app.run(host=self.host, port=self.port, debug=debug, use_reloader=False)