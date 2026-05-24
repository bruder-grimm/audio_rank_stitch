"""
Shared application state for unified recording and playback.

AppState manages thread-safe access to:
- Rankings (word counts)
- Audio buffer cache (loaded word audio segments)
- Graceful shutdown coordination
"""

import json
from pathlib import Path
import threading


class AppState:
    """Thread-safe shared state for recording and playback workers."""

    def __init__(self):
        # Playback settings
        self.attack = 0.1
        self.decay = 0.1
        self.silence_duration = 0.5
        self.shuffle_factor = 0.5
        self.top_k_a = 5
        self.top_k_b = 10

        # Recording flags
        self.instruction_index: int = 0
        self.current_instruction: str = ""
        
        # Control flags
        self.phone_picked_up = threading.Event()
        self.phone_on_hook = threading.Event()
        self.should_record = threading.Event()
        self.should_cycle_instruction = threading.Event()

        self.should_play = threading.Event()

        self.shutdown_requested = threading.Event()
    

    def load_settings(self, settings_file: Path) -> None:
        """Load playback settings from disk."""
        try:
            settings_data = json.loads(settings_file.read_text())
        
            self.attack = settings_data.get("attack", self.attack)
            self.decay = settings_data.get("decay", self.decay)
            self.silence_duration = settings_data.get("silence_duration", self.silence_duration)
            self.shuffle_factor = settings_data.get("shuffle_factor", self.shuffle_factor)
            self.top_k_a = settings_data.get("top_k_a", self.top_k_a)
            self.top_k_b = settings_data.get("top_k_b", self.top_k_b)
        except Exception as e:
            print(f"Error loading settings: {e}")


    def save_settings(self, settings_file: Path):
        """Save playback settings to disk."""
        settings_data = {
            "attack": self.attack,
            "decay": self.decay,
            "silence_duration": self.silence_duration,
            "shuffle_factor": self.shuffle_factor,
            "top_k_a": self.top_k_a,
            "top_k_b": self.top_k_b
        }
        
        settings_file.write_text(json.dumps(settings_data, indent=4))
