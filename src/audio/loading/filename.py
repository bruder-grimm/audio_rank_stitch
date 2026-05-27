
import re


def get_key_from_word(word: str) -> str:
    return re.sub(r'[<>:\".,\'/\\|?*\x00-\x1f]', '', word).strip().lower()