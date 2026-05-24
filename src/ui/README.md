# Web Interfaces Guide

This project includes two web-based frontends to replace the original Tkinter windows for controlling audio playback and recording.

## Overview

### 1. PlaybackSettingsFrontend (Port 5000)
A responsive web interface for controlling audio playback parameters.

**Features:**
- **Attack Slider** (0-100%): Control the attack envelope
- **Decay Slider** (0-100%): Control the decay envelope
- **Silence Duration** (0.1-5s): Set silence between audio playback
- **Shuffle/Spice Factor** (0-100%): Control randomization
- **Top K Words** (1-10): Select how many top words to consider
- **Play Button**: Trigger audio playback
- **Word List Display**: Real-time display of top words with counts

**Access:** Open http://localhost:5000 in your browser

### 2. RecordingFrontend (Port 5001)
A full-screen display interface for recording status and instructions.

**Features:**
- **Instruction Display**: Shows instructions or status text
- **Dynamic Background Color**: Full-screen background that can change color
- **Dynamic Text Color**: Text color can be changed from Python code
- **Minimal, Clean Design**: Distraction-free interface

**Access:** Open http://localhost:5001 in your browser

## Getting Started

### Installation

1. Install Flask dependency:
```bash
pip install -e ".[ui]"
```

Or install Flask directly:
```bash
pip install flask>=3.0.0
```

### Running the Application

#### For Playback Control:
```bash
cd src
python MainPlayback.py
```
This starts:
- The playback worker thread
- Flask server on http://localhost:5000
- Audio playback based on web UI settings

#### For Recording:
```bash
cd src
python MainRecord.py
```
This starts:
- The recording worker thread
- Flask server on http://localhost:5001
- Recording status display on the web interface

## API Reference

### PlaybackSettingsFrontend APIs

#### GET /api/state
Returns current slider values:
```json
{
  "attack": 50,
  "decay": 50,
  "silence_duration": 1.0,
  "shuffle_factor": 50,
  "top_k": 5
}
```

#### POST /api/state
Update slider values:
```json
{
  "attack": 60,
  "decay": 40,
  "silence_duration": 1.5,
  "shuffle_factor": 55,
  "top_k": 7
}
```

#### POST /api/play
Trigger playback action (no parameters).

#### GET /api/words
Get current word list:
```json
{
  "words": [
    {"word": "hello", "count": 5},
    {"word": "world", "count": 3}
  ]
}
```

#### POST /api/words
Update word list from Python code:
```json
{
  "words": [
    {"word": "hello", "count": 5},
    {"word": "world", "count": 3}
  ]
}
```

### RecordingFrontend APIs

#### GET /api/status
Returns current status:
```json
{
  "instruction": "Recording...",
  "background_color": "#ffffff",
  "text_color": "#000000"
}
```

#### POST /api/status
Update instruction text from Python code:
```json
{
  "instruction": "Transcribing..."
}
```

#### GET /api/colors
Get current colors:
```json
{
  "background_color": "#ffffff",
  "text_color": "#000000"
}
```

#### POST /api/colors
Set background and text colors:
```json
{
  "background_color": "#00ff00",
  "text_color": "#ffffff"
}
```

## Python API

### PlaybackSettingsFrontend Class

```python
from ui.playback_server import PlaybackSettingsFrontend

app = PlaybackSettingsFrontend(host="127.0.0.1", port=5000)

# Start server in background thread
import threading
server_thread = threading.Thread(target=app.run, daemon=True)
server_thread.start()

# Access settings
print(app.attack)              # 0.0 to 1.0
print(app.decay)               # 0.0 to 1.0
print(app.silence_duration)    # 0.1 to 5.0 seconds
print(app.shuffle_factor)      # 0.0 to 1.0
print(app.top_k)               # 1 to 10
print(app.play_pressed)        # boolean

# Reset play button
app.play_pressed = False

# Update word list
app.set_words([("word1", 10), ("word2", 5)])
```

### RecordingFrontend Class

```python
from ui.recording_server import RecordingFrontend

app = RecordingFrontend(host="127.0.0.1", port=5001)

# Start server in background thread
import threading
server_thread = threading.Thread(target=app.run, daemon=True)
server_thread.start()

# Update instruction text
app.set_last_sentence("Press spacebar to start recording")

# Change background color
app.set_background_color("#ff0000")  # Red background

# Change text color
app.set_text_color("#ffffff")        # White text
```

## Color Examples

Some common color codes for RecordingFrontend:

| Color | Hex Code | Use Case |
|-------|----------|----------|
| White | #ffffff | Default background |
| Black | #000000 | Default text |
| Red | #ff0000 | Error/Stop |
| Green | #00ff00 | Ready/Recording |
| Yellow | #ffff00 | Warning |
| Blue | #0000ff | Processing |
| Light Gray | #f0f0f0 | Subtle background |

## Browser Compatibility

Both interfaces work with:
- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Notes

- The web servers run on localhost only by default (not accessible from other machines)
- To make them accessible from other machines, change `host` to `"0.0.0.0"`
- The frontend automatically polls for updates every 500ms-1000ms
- Flask debug mode is disabled for production use
- Both interfaces maintain backward compatibility with the original Tkinter implementations
