"""Flaky tests: for-loop iteration over dict without sorted()."""

from for_loop_dict_module import get_scores, get_word_lengths


def test_accumulate_dict_items():
    """FLAKY: for loop over dict.items() without sorted(); order varies with PYTHONHASHSEED."""
    scores = get_scores()
    result = []
    for name, score in scores.items():
        result.append((name, score))
    assert result == [("alice", 5), ("bob", 3), ("charlie", 7), ("diana", 5)]


def test_word_length_keys():
    """FLAKY: list(d.keys()) without sorted(); order varies with PYTHONHASHSEED."""
    lengths = get_word_lengths(["cat", "elephant", "ox"])
    keys = list(lengths.keys())
    assert keys == ["cat", "elephant", "ox"]
