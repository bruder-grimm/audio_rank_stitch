import tkinter as tk
import time
from audio.Record import Recorder
from util.Logger import Logger

class RecordingWindow(tk.Tk):
    def __init__(self, recorder: Recorder, logger: Logger):
        super().__init__()
        self.title("Recorder")
        self.geometry("400x300")

        self.recorder: Recorder = recorder
        self.logger: Logger = logger

        self.is_recording = False
        self.start_time = 0.0
        self.release_job = None

        # last sentence display
        self.last_sentence_text = tk.Text(self,
                                          height=4,
                                          wrap=tk.WORD,
                                          font=("Helvetica", 14))
        self.last_sentence_text.insert(tk.END, "Last sentence will appear here.")
        self.last_sentence_text.config(state=tk.DISABLED)   # read‑only
        self.last_sentence_text.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

        self.status_label = tk.Label(self, text="Press spacebar to start recording", font=("Helvetica", 16))
        self.status_label.pack(padx=20, pady=10)

        self.time_label = tk.Label(self, text="0:00:00", font=("Helvetica", 24))
        self.time_label.pack(padx=20, pady=10)

        # Focus so key events are received
        self.bind("<KeyPress-space>", self.on_space_down)
        self.bind("<KeyRelease-space>", self.on_space_up)
        self.bind("<FocusIn>", lambda e: self.focus_set())


    def on_space_down(self, event):
        if self.release_job is not None:
            self.after_cancel(self.release_job)
            self.release_job = None
            return  # autorepeat press

        self.logger.debug("Spacebar pressed -> Start recording from UI")
        if not self.is_recording:
            self.recorder.start()
            self.is_recording = True
            self.start_time = time.time()
            self.status_label.config(text="Recording...")
            self.update_time()


    def on_space_up(self, event):
        self.release_job = self.after(30, self._handle_release)


    def _handle_release(self):
        self.release_job = None
        self.logger.debug("Spacebar released -> Stop recording from UI")

        if self.is_recording:
            self.recorder.stop()
            self.is_recording = False
            self.status_label.config(text="Recording stopped. Press spacebar to start again.")


    def set_last_sentence(self, sentence: str) -> None:
        """Update the big text field with the latest recorded sentence."""
        self.last_sentence_text.config(state=tk.NORMAL)
        self.last_sentence_text.delete("1.0", tk.END)
        self.last_sentence_text.insert(tk.END, sentence)
        self.last_sentence_text.config(state=tk.DISABLED)

    def update_time(self):
        if self.is_recording:
            elapsed = time.time() - self.start_time
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            millis = int((elapsed % 1) * 1000)
            self.time_label.config(text=f"{hours}:{minutes:02d}:{seconds:02d}:{millis:03d}")
            self.after(100, self.update_time)