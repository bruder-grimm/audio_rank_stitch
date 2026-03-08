import whisperx
import json
import os
import gc
import wave
import threading
import numpy as np
import sounddevice as sd
from pynput import keyboard
from pydub import AudioSegment

# === CONFIGURATION ===
snippets_root = "word_snippets"      # Root folder where all word folders will live
pre_buffer = 0.1                     # Seconds of padding before each word
post_buffer = 0.01                   # Seconds of padding after each word
sample_rate = 16000                  # 16kHz is required by WhisperX
channels = 1                         # Mono audio
device = "cpu"
batch_size = 8
compute_type = "int8"

# === DYNAMIC FILE NAMES (auto-increment recording number) ===
counter = 1
while os.path.exists(f"recording_{counter}.wav"):
    counter += 1
output_wav = f"recording_{counter}.wav"

base_name = os.path.splitext(os.path.basename(output_wav))[0]
json_filename = f"{base_name}_transcription.json"

# =============================================================
# STAGE 1: RECORD AUDIO (hold spacebar)
# =============================================================

def record_audio():
    """Records audio from the microphone while spacebar is held down.
    Saves result as a .wav file."""

    print("\n=== RECORDER ===")
    print("Hold SPACEBAR to record. Release to stop.\n")

    recorded_chunks = []   # Raw audio frames collected during recording
    is_recording = threading.Event()

    def callback(indata, frames, time, status):
        """Called continuously by sounddevice while the stream is open.
        Only saves frames when spacebar is actively held."""
        if is_recording.is_set():
            recorded_chunks.append(indata.copy())

    # Open the audio input stream
    stream = sd.InputStream(
        samplerate=sample_rate,
        channels=channels,
        dtype="int16",
        callback=callback
    )
    stream.start()

    def on_press(key):
        if key == keyboard.Key.space:
            if not is_recording.is_set():
                print("🔴 Recording...")
                is_recording.set()

    def on_release(key):
        if key == keyboard.Key.space:
            print("⏹ Stopped.")
            is_recording.clear()
            return False  # Stop the listener

    # Block here until spacebar is released
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

    stream.stop()
    stream.close()

    if not recorded_chunks:
        print("No audio recorded.")
        exit()

    # Combine all chunks and save to .wav
    audio_data = np.concatenate(recorded_chunks, axis=0)
    with wave.open(output_wav, "w") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit = 2 bytes
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data.tobytes())

    duration = len(audio_data) / sample_rate
    print(f"\n✅ Saved recording: {output_wav} ({duration:.1f} seconds)\n")


# =============================================================
# STAGE 2: TRANSCRIBE WITH WHISPERX
# =============================================================

def transcribe_audio():
    """Runs WhisperX transcription and alignment on the saved wav file.
    Returns the result dict with word-level timestamps.
    Uses cached JSON if available."""

    if os.path.exists(json_filename):
        print(f"Found existing transcription: {json_filename}. Skipping transcription.")
        with open(json_filename, "r", encoding="utf-8") as f:
            return json.load(f)

    print("Transcribing with WhisperX...")
    model = whisperx.load_model("medium.en", device, compute_type=compute_type)
    audio = whisperx.load_audio(output_wav)
    result = model.transcribe(audio, batch_size=batch_size)

    print("Aligning words...")
    model_a, metadata = whisperx.load_align_model(
        language_code=result["language"], device=device
    )
    result = whisperx.align(
        result["segments"], model_a, metadata, audio, device,
        return_char_alignments=False
    )

    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Transcription saved to {json_filename}\n")

    del model
    del model_a
    gc.collect()

    return result


# =============================================================
# STAGE 3: EXTRACT WORD SNIPPETS INTO FOLDERS
# =============================================================

def extract_word_snippets(result):
    """For every word in the transcription, cuts out its audio snippet
    (with pre/post buffer padding) and saves it into a folder named after that word.
    Appends to existing folders if they already exist."""

    print("Extracting word snippets...\n")

    # Load the full recording as a pydub AudioSegment (millisecond-based)
    full_audio = AudioSegment.from_wav(output_wav)
    audio_duration_ms = len(full_audio)

    os.makedirs(snippets_root, exist_ok=True)

    # Track how many snippets exist per word so we can number them correctly
    # (accounts for snippets from previous runs already in the folder)
    existing_counts = {}

    total_snippets = 0

    for segment in result["segments"]:
        for word_data in segment.get("words", []):

            raw_word = word_data.get("word", "").strip()
            start_s = word_data.get("start")
            end_s = word_data.get("end")

            # Skip words with missing timestamps (sometimes happens at segment edges)
            if start_s is None or end_s is None:
                continue

            # Clean the word to make it safe as a folder/filename
            clean_word = "".join(
                c for c in raw_word.lower() if c.isalpha()
            )
            if not clean_word:
                continue

            # Create the folder for this word if it doesn't exist
            folder_path = os.path.join(snippets_root, clean_word)
            os.makedirs(folder_path, exist_ok=True)

            # Count existing files to determine next snippet number
            if clean_word not in existing_counts:
                existing_files = [
                    f for f in os.listdir(folder_path) if f.endswith(".wav")
                ]
                existing_counts[clean_word] = len(existing_files)

            snippet_index = existing_counts[clean_word] + 1
            existing_counts[clean_word] += 1

            # Apply pre/post buffer, clamp to audio bounds (in milliseconds)
            start_ms = max(0, int((start_s - pre_buffer) * 1000))
            end_ms = min(audio_duration_ms, int((end_s + post_buffer) * 1000))

            # Cut and export the snippet
            snippet = full_audio[start_ms:end_ms]
            snippet_filename = f"{clean_word}_{snippet_index:04d}.wav"
            snippet_path = os.path.join(folder_path, snippet_filename)
            snippet.export(snippet_path, format="wav")

            total_snippets += 1
            print(f"  [{total_snippets}] '{raw_word}' → {snippet_path}")

    print(f"\n✅ Done! {total_snippets} snippets saved to '{snippets_root}/'")




# =============================================================
# STAGE 4: UPDATE CUMULATIVE WORD RANKING
# =============================================================

def update_word_ranking(result):
    """Counts words in this recording, merges with the cumulative ranking
    file, and rewrites it — showing only words that appear more than once
    across all recordings combined, sorted by frequency."""

    ranking_path = os.path.join(snippets_root, "_word_ranking.json")

    # Load existing cumulative counts if the file exists
    cumulative = {}
    if os.path.exists(ranking_path):
        with open(ranking_path, "r", encoding="utf-8") as f:
            cumulative = json.load(f)

    # Count words in this recording
    this_recording = {}
    for segment in result["segments"]:
        for word_data in segment.get("words", []):
            clean_word = "".join(
                c for c in word_data.get("word", "").lower() if c.isalpha()
            )
            if clean_word:
                this_recording[clean_word] = this_recording.get(clean_word, 0) + 1

    # Merge into cumulative totals
    for word, count in this_recording.items():
        cumulative[word] = cumulative.get(word, 0) + count

    # Filter to words seen more than once, sort by frequency descending
    filtered = {w: c for w, c in cumulative.items() if c > 1}
    ranked = sorted(filtered.items(), key=lambda x: x[1], reverse=True)

    # Write updated ranking file as JSON (sorted by frequency descending)
    os.makedirs(snippets_root, exist_ok=True)
    ranked_dict = {word: count for word, count in ranked}
    with open(ranking_path, "w", encoding="utf-8") as f:
        json.dump(ranked_dict, f, indent=2)

    print(f"\n📊 Word ranking updated → {ranking_path} ({len(ranked)} words)\n")

# =============================================================
# MAIN
# =============================================================

if __name__ == "__main__":
    record_audio()
    result = transcribe_audio()
    extract_word_snippets(result)
    update_word_ranking(result)