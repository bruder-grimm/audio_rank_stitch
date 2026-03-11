from pathlib import Path

from util.Logger import LogLevel

# Loglevel 
LOGLEVEL = LogLevel.DEBUG

# Config for our Recordings
SAMPLERATE = 44100
PATH = Path(__file__).resolve().parent / "../word_snippets"

# WhisperX config (don't touch that sample rate)
# Buffer sizes are in millis
WHISPERX_SAMPLERATE = 16000
AUDIO_SNIPPET_PRE_BUFFER = 0.1  
AUDIO_SNIPPET_POST_BUFFER = 0.01