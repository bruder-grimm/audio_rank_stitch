import json
import os
from pydub import AudioSegment

# === CONFIGURATION ===
snippets_root = "word_snippets"           # Must match the recorder script
ranking_file = os.path.join(snippets_root, "_word_ranking.json")
output_file = "ranked_stitched.wav"       # Final output file
gap_ms = 100                              # Silence gap between each word snippet (milliseconds)
word_gap_ms = 800                         # Extra silence gap between different words

# =============================================================
# LOAD RANKING
# =============================================================

if not os.path.exists(ranking_file):
    print(f"❌ Ranking file not found: {ranking_file}")
    print("Run the recorder script first to generate it.")
    exit()

with open(ranking_file, "r", encoding="utf-8") as f:
    ranking = json.load(f)

# JSON is already sorted by frequency, but sort again to be safe
ranked_words = sorted(ranking.items(), key=lambda x: x[1], reverse=True)

print(f"📋 Loaded ranking: {len(ranked_words)} words\n")

# =============================================================
# STITCH AUDIO
# =============================================================

silence = AudioSegment.silent(duration=gap_ms)
final_audio = AudioSegment.empty()
used = []
skipped = []

for word, count in ranked_words:
    folder_path = os.path.join(snippets_root, word)

    if not os.path.exists(folder_path):
        skipped.append((word, "folder missing"))
        continue

    # Get all wav snippets for this word, sorted by name (which is by index)
    snippets = sorted([f for f in os.listdir(folder_path) if f.endswith(".wav")])

    if not snippets:
        skipped.append((word, "no wav files"))
        continue

    try:
        word_audio = AudioSegment.empty()
        for snippet_file in snippets:
            snippet_path = os.path.join(folder_path, snippet_file)
            clip = AudioSegment.from_wav(snippet_path)
            word_audio += clip + silence

        final_audio += word_audio + AudioSegment.silent(duration=word_gap_ms)
        used.append((word, count, len(snippets)))
        print(f"  ✅ '{word}' ({count}x) → {len(snippets)} snippet(s) played")
    except Exception as e:
        skipped.append((word, str(e)))
        print(f"  ⚠️  '{word}' skipped — {e}")

# =============================================================
# EXPORT
# =============================================================

if len(final_audio) == 0:
    print("\n❌ No audio was stitched. Check your word_snippets folder.")
    exit()

final_audio.export(output_file, format="wav")

duration_s = len(final_audio) / 1000
total_snippets = sum(n for _, _, n in used)
print(f"\n✅ Stitched {len(used)} words ({total_snippets} total snippets) → {output_file} ({duration_s:.1f} seconds)")

if skipped:
    print(f"\n⚠️  Skipped {len(skipped)} words:")
    for word, reason in skipped:
        print(f"   - '{word}': {reason}")