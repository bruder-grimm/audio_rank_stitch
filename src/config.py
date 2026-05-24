from enum import Enum
from pathlib import Path

from util.logger import LogLevel

# Loglevel 
LOGLEVEL = LogLevel.DEBUG

# Confgure where the speakers and where the phone is connected
class CHANNEL(Enum):
    LEFT = 0
    RIGHT = 1

PHONE_CHANNEL = CHANNEL.LEFT
SPEAKER_CHANNEL = CHANNEL.RIGHT

# Config for our Recordings
SAMPLERATE = 44100
PATH = Path(__file__).resolve().parent / "../word_snippets"

# WhisperX config (don't touch that sample rate)
# Buffer sizes are in millis
WHISPERX_SAMPLERATE = 16000
AUDIO_SNIPPET_PRE_BUFFER = 0.2
AUDIO_SNIPPET_POST_BUFFER = 0.2

PLAYBACK_BLOCKSIZE = 1024

INSTRUCTIONS = [
    "Tell me about your last dream. What did it mean to you?",
    "Which kind of sausage is your favourite?",
    "When was the last time you were afraid to do something?",
]