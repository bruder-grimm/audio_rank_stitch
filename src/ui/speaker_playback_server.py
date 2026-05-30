from flask import Flask, render_template, jsonify, request
from app_state import AppState
from util.logger import Logger


class PlaybackSettingsFrontend:
    """Web-based frontend for playback settings control."""

    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    def __init__(
            self, 
            app_state: AppState,
            logger: Logger,
            host: str = "0.0.0.0", 
            port: int = 5000, 
        ):
        self.logger = logger
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
            "attack": self._app_state.attack * 1000,
            "decay": self._app_state.decay * 1000,
            "silence_duration": self._app_state.silence_duration,
            "shuffle_factor": self._app_state.temperature,
            "top_k_a": self._app_state.top_k_a,
            "top_k_b": self._app_state.top_k_b,
            "pre_trim": self._app_state.pre_trim * 1000,
            "post_trim": self._app_state.post_trim * 1000,
            "run_the_list": self._app_state.run_the_list,
            "silence_stray": self._app_state.silence_stray,
            "is_playing": self._app_state.should_play.is_set(),
            "sentence_length": self._app_state.sentence_length,
        }
        return jsonify(settings)
    
    def _update_state(self):
        """Update slider values from client to AppState."""
        data = request.json

        # Fallback: local state only
        if "attack" in data:
            attack = data["attack"] / 1000
            self.logger.info(f"Setting attack to {attack}")
            self._app_state.attack = attack
        if "decay" in data:
            decay = data["decay"] / 1000
            self.logger.info(f"Setting decay to {decay}")
            self._app_state.decay = decay
        if "silence_duration" in data:
            self._app_state.silence_duration = data["silence_duration"]
            self.logger.info(f"Setting silence_duration to {data["silence_duration"]}")
        if "shuffle_factor" in data:
            self._app_state.temperature = data["shuffle_factor"]
            self.logger.info(f"Setting shuffle_factor to {data["shuffle_factor"]}")
        if "top_k_a" in data:
            self._app_state.top_k_a = data["top_k_a"]
            self.logger.info(f"Setting top_k_a to {data["top_k_a"]}")
        if "top_k_b" in data:
            self._app_state.top_k_b = data["top_k_b"]
            self.logger.info(f"Setting top_k_b to {data["top_k_b"]}")
        if "pre_trim" in data:
            pre_trim = data["pre_trim"] / 1000
            self.logger.info(f"Setting pre_trim to {pre_trim}")
            self._app_state.pre_trim = pre_trim
        if "post_trim" in data:
            post_trim = data["post_trim"] / 1000
            self.logger.info(f"Setting post_trim to {post_trim}")
            self._app_state.post_trim = post_trim
        if "run_the_list" in data:
            self.logger.info(f"Setting run the list to {data["run_the_list"]}")
            self._app_state.run_the_list = data["run_the_list"]
        if "silence_stray" in data:
            self.logger.info(f"Setting stray around silence to {data["silence_stray"]}")
            self._app_state.silence_stray = data["silence_stray"]
        if "sentence_length" in data:
            self.logger.info(f"Setting sentence length to {data["sentence_length"]}")
            self._app_state.sentence_length = data["sentence_length"]

        self._app_state.playback_dirty.set()
        
        return jsonify({"status": "ok"})
    
    def _play(self):
        """Handle play button press."""
        if not self._app_state.should_play.is_set():
            self._app_state.should_play.set()
        else:
            self._app_state.should_play.clear()

        return jsonify({"status": "ok"})
    
    def _get_words(self):
        words = self._app_state.get_current_top_k_selection()
        return jsonify({
            "words": [
                {"word": w, "count": c}
                for w, c in words.items()
            ]
        })
    
    def run(self, debug: bool) -> None:
        """Start the Flask server in a thread."""
        self.logger.info(f"Starting Flask on http://{self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port, debug=debug, use_reloader=False)
