import tkinter as tk
from tkinter import ttk
from typing import Optional, Any

from audio.Play import Player
from util.logger import Logger

class PlaybackWindow(tk.Tk):
    def __init__(self, audio_player: Player, logger: Logger):
        super().__init__()
        self.title("Audio Playback Window")
        self.geometry("400x400")

        self.logger: Logger = logger
        self.audio_player: Player = audio_player
        self.words: Optional[dict[str, int]] = None

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
            from_=0.1,
            to=5.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            label="Silence (s)"
        )
        self.silence_slider.set(1.0)
        self.silence_slider.pack(fill=tk.X, padx=5, pady=2)

        # play button
        self.play_button = ttk.Button(self, text="Play", command=self.play_audio)
        self.play_button.pack(pady=10)

    def set_words(self, words: dict[str, int]):
        self.words = words
        self.listbox.delete(0, tk.END)  # Clear existing items
        for word, count in words.items():
            self.listbox.insert(tk.END, f"{word}: {count}")

    @property
    def attack(self) -> float:
        """Attack value in percent (0–100)."""
        return self.attack_slider.get()

    @property
    def decay(self) -> float:
        """Decay value in percent (0–100)."""
        return self.decay_slider.get()

    @property
    def silence_duration(self) -> float:
        """Silence duration in seconds (0.1–5)."""
        return self.silence_slider.get()

    def play_audio(self):
        # placeholder for real playback; audio_player can be used here
        self.logger.info(
            "Playing audio with "
            f"attack={self.attack}%, decay={self.decay}%, "
            f"silence={self.silence_duration}s"
        )
        # e.g. self.audio_player.play(...)
