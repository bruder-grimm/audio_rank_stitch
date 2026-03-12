import tkinter as tk
from tkinter import ttk
from typing import Optional, Any

from audio.playback_record.Play import Player
from util.Logger import Logger

class PlaybackWindow(tk.Tk):
    def __init__(self, audio_player: Player, logger: Logger):
        super().__init__()
        self.title("Audio Playback Window")
        self.geometry("500x700")

        self.logger: Logger = logger
        self.audio_player: Player = audio_player
        self.words: Optional[list[tuple[str, int]]] = None
        self._play_pressed = False  

        # word‑count list
        self.listbox = tk.Listbox(self)
        self.listbox.pack(pady=10, fill=tk.BOTH, expand=True)

        # sliders frame
        frame = ttk.Frame(self)
        frame.pack(pady=10, fill=tk.X, expand=False)

        # attack slider (0‑100 %)
        self.attack_slider = tk.Scale(
            frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            label="Attack (%)"
        )
        self.attack_slider.set(50)  # default
        self.attack_slider.pack(fill=tk.X, padx=5, pady=2)

        # decay slider (0‑100 %)
        self.decay_slider = tk.Scale(
            frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            label="Decay (%)"
        )
        self.decay_slider.set(50)
        self.decay_slider.pack(fill=tk.X, padx=5, pady=2)

        # silence duration slider (0.1‑5 s)
        self.silence_slider = tk.Scale(
            frame,
            from_=0.0,
            to=5.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            label="Silence (s)"
        )
        self.silence_slider.set(1.0)
        self.silence_slider.pack(fill=tk.X, padx=5, pady=2)

        # spice slider (0‑100 %)
        self.spice_slider = tk.Scale(
            frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            label="Spice"
        )
        self.spice_slider.set(50)
        self.spice_slider.pack(fill=tk.X, padx=5, pady=2)

        self.top_k_slider = tk.Scale(
            frame,
            from_=1,
            to=10,
            orient=tk.HORIZONTAL,
            label="Top K Words",
            resolution=1
        )
        self.top_k_slider.set(5)
        self.top_k_slider.pack(fill=tk.X, padx=5, pady=2)

        # play button
        self.play_button = ttk.Button(self, text="Play", command=self._on_play_pressed)
        self.play_button.pack(pady=10)

    def _on_play_pressed(self):
        """Set the play pressed flag when button is clicked."""
        self._play_pressed = True

    def set_words(self, words: list[tuple[str, int]]):
        self.words = words
        self.listbox.delete(0, tk.END)  # Clear existing items
        for word, count in words:
            self.listbox.insert(tk.END, f"{word}: {count}")

    @property
    def shuffle_factor(self) -> float:
        """Shuffle factor between 0 and 1"""
        return self.spice_slider.get() * 0.01

    @property
    def attack(self) -> float:
        """Attack value between 0 and 1"""
        return self.attack_slider.get() * 0.01

    @property
    def decay(self) -> float:
        """Decay value between 0 and 1"""
        return self.decay_slider.get() * 0.01

    @property
    def silence_duration(self) -> float:
        """Silence duration in seconds (0.1–5)."""
        return self.silence_slider.get()
    
    @property
    def top_k(self) -> int:
        """Number of top words to consider (based on listbox items)."""
        return int(self.top_k_slider.get())

    @property
    def play_pressed(self) -> bool:
        """Returns True if the play button was pressed since last check."""
        return self._play_pressed

    @play_pressed.setter
    def play_pressed(self, value: bool):
        """Reset the play pressed flag."""
        self._play_pressed = value
