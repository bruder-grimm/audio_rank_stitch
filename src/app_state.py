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

from config import INSTRUCTIONS
from ranking.rankings import Rankings


class AppState:
    """Thread-safe shared state for recording and playback workers."""

    def __init__(self, rankings: Rankings, settings_path: Path) -> None:
        self.settings_path = settings_path

        # Playback settings
        self.attack = 0.1
        self.decay = 0.1
        self.silence_duration = 0.5
        self.shuffle_factor = 0.5
        self.top_k_a = 5
        self.top_k_b = 10
        self.pre_trim = 0.0
        self.post_trim = 0.0

        # Recording flags
        self.instruction_index: int = 0
        self.current_instruction: str = ""

        # Rankings
        self._rankings: Rankings = rankings
        self.current_top_k_selection: dict[str, int] = {}
        
        # Control flags
        self.phone_picked_up = threading.Event()
        self.should_record = threading.Event()
        self.playback_dirty = threading.Event()
        self.should_play = threading.Event()
        self.shutdown_requested = threading.Event()
        
        # Locks
        self.instruction_lock = threading.Lock()
        self.state_lock = threading.Lock()

        self._load_settings()


    def cycle_instruction(self):
        """Cycle to the next instruction."""
        with self.instruction_lock:
            self.instruction_index = (self.instruction_index + 1) % len(INSTRUCTIONS)
            self.current_instruction = INSTRUCTIONS[self.instruction_index]

    def get_current_instruction(self):
        """Get the current instruction."""
        with self.instruction_lock:
            return self.current_instruction
        
    def increment_ranking(self, word: str, count: int = 1):
        """Increment the ranking count for a word."""
        self._rankings.update_with({word: count})

    def get_rankings_snapshot(self) -> dict[str, int]:
        """Get a thread-safe snapshot of the current rankings."""
        return self._rankings.get_top_k_words(100)
        
    def set_current_top_k_word_selection(self, top_k_selection: dict[str, int]):
        """Set the current top-k selection"""
        with self.state_lock:
            self.current_top_k_selection = top_k_selection

    def get_current_top_k_selection(self) -> dict[str, int]:
        """Get the current top-k selection"""
        with self.state_lock:
            return self.current_top_k_selection

    def heapify_rankings(self):
        """Heapify the rankings for efficient retrieval."""
        self._rankings.heapify()
    
    def shutdown(self):
        """Signal all threads to shut down."""
        self.shutdown_requested.set()
        self._save_settings()

    def _load_settings(self) -> None:
        """Load playback settings from disk."""
        try:
            settings_data = json.loads(self.settings_path.read_text())
        
            self.attack = settings_data.get("attack", self.attack)
            self.decay = settings_data.get("decay", self.decay)
            self.silence_duration = settings_data.get("silence_duration", self.silence_duration)
            self.shuffle_factor = settings_data.get("shuffle_factor", self.shuffle_factor)
            self.top_k_a = settings_data.get("top_k_a", self.top_k_a)
            self.top_k_b = settings_data.get("top_k_b", self.top_k_b)
            self.pre_trim = settings_data.get("pre_trim", self.pre_trim)
            self.post_trim = settings_data.get("post_trim", self.post_trim)
        except Exception as e:
            print(f"Error loading settings: {e}")


    def _save_settings(self):
        """Save playback settings to disk."""
        settings_data = {
            "attack": self.attack,
            "decay": self.decay,
            "silence_duration": self.silence_duration,
            "shuffle_factor": self.shuffle_factor,
            "top_k_a": self.top_k_a,
            "top_k_b": self.top_k_b,
            "pre_trim": self.pre_trim,
            "post_trim": self.post_trim,
        }
        
        self.settings_path.write_text(json.dumps(settings_data, indent=4))
