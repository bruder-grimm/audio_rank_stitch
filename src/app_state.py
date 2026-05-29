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
from ranking.embedding import PosEmbeddingProvider
from ranking.markov import PosMarkovModel
from ranking.rankings import Rankings


class AppState:
    """Thread-safe shared state for recording and playback workers."""

    def __init__(
            self, 
            rankings: Rankings, 
            markov_model: PosMarkovModel, 
            embeddings_provider: PosEmbeddingProvider,
            settings_path: Path
        ) -> None:
        # Path for saving our playback settings
        self.settings_path = settings_path

        # Playback settings
        self.attack: float = 0.1
        self.decay: float = 0.1
        self.silence_duration: float = 0.5
        self.temperature: float = 0.5
        self.top_k_a: int = 5
        self.top_k_b: int = 10
        self.pre_trim: float = 0.0
        self.post_trim: float = 0.0

        # Recording flags
        self.instruction_index: int = 0
        self.current_instruction: str = ""

        # Rankings
        self.rankings: Rankings = rankings
        self.markov_model: PosMarkovModel = markov_model
        self.current_top_k_selection: dict[str, int] = {}
        self.embeddings_provider: PosEmbeddingProvider = embeddings_provider
        
        # Control flags
        self.phone_picked_up = threading.Event()
        self.playback_dirty = threading.Event()
        self.should_play = threading.Event()
        self.shutdown_requested = threading.Event()
        self.run_the_list: bool = False
        
        # Locks
        self.instruction_lock = threading.Lock()

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
        
    def get_current_top_k_selection(self) -> dict[str, int]:
        """Get the current top-k selection"""
        return self.markov_model.get_most_frequent_words(self.top_k_a, self.top_k_b)

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
            self.temperature = settings_data.get("shuffle_factor", self.temperature)
            self.top_k_a = settings_data.get("top_k_a", self.top_k_a)
            self.top_k_b = settings_data.get("top_k_b", self.top_k_b)
            self.pre_trim = settings_data.get("pre_trim", self.pre_trim)
            self.post_trim = settings_data.get("post_trim", self.post_trim)
            self.instruction_index = settings_data.get("instruction_index", self.instruction_index)
            self.current_instruction = settings_data.get("current_instruction", self.current_instruction)
        except Exception as e:
            print(f"Error loading settings: {e}")


    def _save_settings(self):
        """Save playback settings to disk."""
        settings_data = {
            "attack": self.attack,
            "decay": self.decay,
            "silence_duration": self.silence_duration,
            "shuffle_factor": self.temperature,
            "top_k_a": self.top_k_a,
            "top_k_b": self.top_k_b,
            "pre_trim": self.pre_trim,
            "post_trim": self.post_trim,
            "instruction_index": self.instruction_index,
            "current_instruction": self.current_instruction,
        }
        
        self.settings_path.write_text(json.dumps(settings_data, indent=4))
