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
    "How do you increase revenue in a fast paced business environment?",
    "Tell me about somebody who you know you will never see again.",
    "When was the last time you felt that time was moving slowly.",
    "When was the last time you felt that time was moving fast.",
    "Why are you here?",
    "How did you get here?",
    "What is old in your home?",
    "What is your most valued thing?",
    "What is the most valuable thing you own?",
    "When did you find out what it's all about?",
    "What was your last memorable interaction with a stranger?",
    "Turn around, narrate what is happening behind the window.",
    "What would you do if today was the last day…",
    "Recount your oldest memory",
    "What were you doing the last time you got lost",
    "What is the first 3 things you do when you get home?",
    "Tell me the recipe of your best dish, step by step.",
    "How do you increase revenue in a fast paced business environment?",
    "What was the story of the last movie you watched?",
    "Recount a vivid dream.",
    "Tell me about your last memorable sunset.",
    "What would you be doing in the summer of 69?",
    "What's the ROI (return on investment) of being alive?",
    "What is your best friend doing right now?",
    "What is holding your life together?",
    "Explain something complicated",
    "Where would you be if time did not matter?",
    "What's the first thing you would do if you won the lottery?",
    "Tell me about something that you will never see again.",
    "What is something you want to lose?",
    "What is a healthy meal?",
    "Read to me the last message you sent.",
    "Why did you not become an olympic athlete?",
    "What is holy to you?",
    "What is friendship to you and your friends?",
    "What were you born too late for?",
    "What is your favorite thing to get at the gas station?",
    "What's in your weekly groceries.",
    "What are you addicted to?",
    "What is your favorite thing to do when you are truly alone?",
    "Why was something taken away from you?",
    "Tell me a joke",
    "Tell me about a person that you only know through other people's memories ",
    "What would you like to be reborn as?",
    "Would you still love me if I was a worm?",
    "Describe your perfect garden",
    "What makes you feel young?",
    "What scared you as a child?",
    "What makes you feel old?",
]