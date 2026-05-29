from enum import Enum
from pathlib import Path

from util.logger import LogLevel

# Loglevel 
LOGLEVEL = LogLevel.DEBUG

# Artistry
SENTENCE_LENGTH = 30

# Confgure where the speakers and where the phone is connected
class CHANNEL(Enum):
    LEFT = 0
    RIGHT = 1

PHONE_CHANNEL = CHANNEL.LEFT
SPEAKER_CHANNEL = CHANNEL.RIGHT

# Config for our Recordings
SAMPLERATE = 44100
AUDIO_SNIPPET_PATH = Path(__file__).resolve().parent / "../word_snippets"

# WhisperX config (don't touch that sample rate)
# Buffer sizes are in millis
WHISPERX_SAMPLERATE = 16000
AUDIO_SNIPPET_PRE_BUFFER = 0.3
AUDIO_SNIPPET_POST_BUFFER = 0.3

PRE_DIAL_DELAY_SECONDS = 0.7
POST_RECORDING_PROCESSING_DELAY_SECONDS = 10

PLAYBACK_BLOCKSIZE = 1024

RECORDING_PORT = 1234
PLAYBACK_PORT = 5678

INSTRUCTIONS = [
    "Where did cotton eye joe come from?",
    "Where did cotton eye joe go?",
    "What is your favourite snack from the gas station?",
]