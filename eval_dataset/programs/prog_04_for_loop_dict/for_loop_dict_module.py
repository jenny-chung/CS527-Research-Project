"""Sample module: returns a dict whose insertion order depends on set iteration."""


def get_scores():
    """Return a dict built from a set; insertion order varies with PYTHONHASHSEED."""
    players = {"alice", "bob", "charlie", "diana"}
    return {p: len(p) for p in players}


def get_word_lengths(words):
    """Return a dict mapping each word to its length."""
    word_set = set(words)
    return {w: len(w) for w in word_set}
