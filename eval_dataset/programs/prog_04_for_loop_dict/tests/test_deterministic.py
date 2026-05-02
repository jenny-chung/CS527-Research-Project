"""Deterministic tests: properly ordered dict iteration."""

from for_loop_dict_module import get_scores, get_word_lengths


def test_accumulate_dict_items_sorted():
    """DETERMINISTIC: for loop over sorted(dict.items())."""
    scores = get_scores()
    result = []
    for name, score in sorted(scores.items()):
        result.append((name, score))
    assert result == [("alice", 5), ("bob", 3), ("charlie", 7), ("diana", 5)]


def test_word_length_keys_sorted():
    """DETERMINISTIC: sorted(d.keys()) is always alphabetical."""
    lengths = get_word_lengths(["cat", "elephant", "ox"])
    keys = sorted(lengths.keys())
    assert keys == ["cat", "elephant", "ox"]
