import re

def keep_words_and_numbers(s: str) -> str:
    return re.sub(r"[^\w\s]", "", s)