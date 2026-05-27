from flask import Flask, render_template, jsonify, request
from app_state import AppState


class PlaybackSettingsFrontend:
    """Web-based frontend for playback settings control."""
    
    def __init__(
            self, 
            app_state: AppState,
            host: str = "0.0.0.0", 
            port: int = 5000, 
        ):
        self.host = host
        self.port = port
        self._app_state = app_state
        self.app = Flask(__name__, 
                        template_folder="playback_templates",
                        static_folder="playback_static")
        
        # Register routes
        self.app.route("/")(self._index)
        self.app.route("/api/state", methods=["GET"])(self._get_state)
        self.app.route("/api/state", methods=["POST"])(self._update_state)
        self.app.route("/api/play", methods=["POST"])(self._play)
        self.app.route("/api/words", methods=["GET"])(self._get_words)
    
    def _index(self):
        """Serve main HTML page."""
        return render_template("index.html")
    
    def _get_state(self):
        """Get current state of all sliders from AppState or defaults."""
        settings = {
            "attack": self._app_state.attack,
            "decay": self._app_state.decay,
            "silence_duration": self._app_state.silence_duration,
            "shuffle_factor": self._app_state.shuffle_factor,
            "top_k_a": self._app_state.top_k_a,
            "top_k_b": self._app_state.top_k_b,
        }
        return jsonify(settings)
    
    def _update_state(self):
        """Update slider values from client to AppState."""
        data = request.json
    
        # Fallback: local state only
        if "attack" in data:
            self._app_state.attack = data["attack"]
        if "decay" in data:
            self._app_state.decay = data["decay"]
        if "silence_duration" in data:
            self._app_state.silence_duration = data["silence_duration"]
        if "shuffle_factor" in data:
            self._app_state.shuffle_factor = data["shuffle_factor"]
        if "top_k_a" in data:
            self._app_state.top_k_a = data["top_k_a"]
        if "top_k_b" in data:
            self._app_state.top_k_b = data["top_k_b"]
        
        return jsonify({"status": "ok"})
    
    def _play(self):
        """Handle play button press."""
        if not self._app_state.should_play.is_set():
            self._app_state.should_play.set()
        else:
            self._app_state.should_play.clear()

        return jsonify({"status": "ok"})
    
    def _get_words(self):
        """Get list of words to display."""
        return jsonify({"words": self._app_state.get_current_top_k_selection()})
    
    def run(self, debug: bool = False):
        """Start the Flask server in a thread."""
        self.app.run(host=self.host, port=self.port, debug=debug, use_reloader=False)
    
    # Properties for worker thread access
    @property
    def shuffle_factor(self) -> float:
        """Shuffle factor between 0 and 1."""
        return self._app_state.shuffle_factor * 0.01
    
    @property
    def attack(self) -> float:
        """Attack value between 0 and 1."""
        return self._app_state.attack * 0.01
    
    @property
    def decay(self) -> float:
        """Decay value between 0 and 1."""
        return self._app_state.decay * 0.01
    
    @property
    def silence_duration(self) -> float:
        """Silence duration in seconds (0.1–5)."""
        return self._app_state.silence_duration
    
    @property
    def top_k_a(self) -> int:
        """Number of top words to consider."""
        return self._app_state.top_k_a

    @property
    def top_k_b(self) -> int:
        """Number of top words to consider."""
        return self._app_state.top_k_b
    
    @property
    def play_pressed(self) -> bool:
        if self._app_state.should_play.is_set():
            self._app_state.should_play.clear()
            return True
        return False

