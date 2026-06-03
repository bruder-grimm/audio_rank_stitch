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

# Config for our Recordings and playback
SAMPLERATE = 44100
LOWPASS_FREQ = 8000 # in hz
AUDIO_SNIPPET_PATH = Path(__file__).resolve().parent / "../word_snippets"

# WhisperX config (don't touch that sample rate)
# Buffer sizes are in seconds
WHISPERX_SAMPLERATE = 16000
AUDIO_SNIPPET_PRE_BUFFER = 0.3
AUDIO_SNIPPET_POST_BUFFER = 0.3

PRE_DIAL_DELAY_SECONDS = 0.7
POST_RECORDING_PROCESSING_DELAY_SECONDS = 10

PLAYBACK_BLOCKSIZE = 1024

RECORDING_PORT = 1234
PLAYBACK_PORT = 5678

INSTRUCTIONS = [
    "How did you get here?",
    "Where did cotton eye joe come from?",
    "Where did cotton eye joe go?",
    "What is a cotton eye?",
    "Can you recite a poem?",
    "What was the plot of the last movie you watched?",
    "What is the first 3 things you do when you get home?",
    "What is your favorite thing to get at the gas station?",
    "What's in your weekly groceries.",
    "How did you get here?",
    "Where did cotton eye joe come from?",
    "Tell me a memory about water.",
    "Recount your oldest memory...",
    "What were you doing the last time you got lost.",
    "What is the first 3 things you do when you get home?",
    "Recount a vivid dream.",
    "How do you make your coffee in the morning?",
    "How did you get here?",
    "***JOKER*** Tell me whatever…",
    "What were you doing the last time you had sore legs?",
    "What were you doing the last time you got lost.",
    "Tell me the recipe of your best dish, step by step.",
    "How do you increase revenue in a fast paced business environment?",
    "What was the plot of the last movie you watched?",
    "Recount a vivid dream.",
    "Have you had Deja Vu, what was it about?",
    "Tell me a memory about water.",
    "Tell me about your last memorable sunset.",
    "What would you be doing in the summer of 69?",
    "What's the ROI of being alive?",
    "Recount your oldest memory...",
    "What were you doing the last time you got lost.",
    "Recount your oldest memory...",
    "What is a secret your parents kept from you?",
    "Recount a vivid dream.",
    "What is your best friend doing right now?",
    "Find somebody in your surroundings, narrate their actions as they happen.",
    "How do you increase revenue in a fast paced business environment?",
    "What were you doing the last time you got lost.",
    "Recount a vivid dream.",
    "Have you had Deja Vu, what was it about?",
    "Tell me a memory about water.",
    "Tell me about your last memorable sunset.",
    "What would you be doing in the summer of 69?",
    "What's the ROI of being alive?",
    "Recount your oldest memory...",
    "What were you doing the last time you got lost.",
    "Recount your oldest memory...",
    "What is a secret your parents kept from you?",
    "Recount a vivid dream.",
    "What is your best friend doing right now?",
    "Find somebody in your surroundings, narrate their actions as they happen.",
    "How do you increase revenue in a fast paced business environment?",
    "What were you doing the last time you got lost.",
    "Why did you not become an olympic athlete?",
    "Recount a vivid dream.",
    "What do you see in the other art works in here.",
    "Recite the lyrics of the first song you thought about",
    "Tell me a memory about water.",
    "What do you see in the other people in here.",
    "What are you afraid is hidden in this cave?",
    "Express yourself!",
    "Recount a vivid dream.",
    "What were you doing the last time you got lost.",
    "What is your best friend doing right now?",
    "How did you get here?",
    "Why are you here?",
    "Recount your oldest memory...",
    "What is holy to you?",
    "What is holding your life together?",
    "Recount a vivid dream.",
    "What do you see in the other art works in here.",
    "Recite the lyrics of the first song you thought about",
    "Tell me a memory about water.",
    "What do you see in the other people in here.",
    "Express yourself!",
    "Recount a vivid dream.",
    "What were you doing the last time you got lost.",
    "What is your best friend doing right now?",
    "How did you get here?",
    "Why are you here?",
    "Recount your oldest memory...",
    "What is holy to you?",
    "What is holding your life together?",
    "What would your friends say about you?",
    "What makes you think you are a good person?",
    "How do you see yourself?",
    "What are you afraid is hidden in this cave?",
]