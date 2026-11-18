# grapheme_cluster_segmenter

Splits a string into user-perceived characters using the extended grapheme
cluster rules from Unicode Standard Annex #29, including combining marks,
Hangul jamo sequences, regional indicator pairs, and ZWJ emoji sequences.

```python
from grapheme_cluster_segmenter import split_graphemes, GraphemeClusterSegmenter

split_graphemes("e\u0301")
# ['e\u0301']

split_graphemes("\U0001F469\u200D\U0001F467")
# ['\U0001F469\u200D\U0001F467']

seg = GraphemeClusterSegmenter("a\u0301b")
len(seg)
# 2
list(seg)
# ['a\u0301', 'b']
```

## Why this exists

Counting characters with `len()` counts code points, not what a reader sees as a
single character. A combining mark, a Hangul syllable written as jamo, or an
emoji ZWJ sequence all appear as one character but span several code points.
This library groups those code points into clusters so that iteration, slicing,
and length match human perception.

The trade-off is that the implementation is a focused subset of UAX #29 rather
than a table-driven full implementation. It uses Python's `unicodedata`
category data and hand-written ranges for the properties `unicodedata` does not
expose, such as Extended_Pictographic. That keeps the library dependency-free
and small, at the cost of not covering every rare code point in the standard's
tables. The rules that matter for everyday text, combining sequences, emoji, and
Hangul are implemented and tested.

## The awkward edge

The regional indicator rule pairs flags two code points at a time. A run of
three regional indicators produces two clusters: the first two form a flag, and
the third stands alone until another regional indicator follows it. This matches
UAX #29, but it surprises people who expect every pair to be a flag. The
segmenter is stateless, so a lone trailing regional indicator is not
retroactively joined when more text arrives later — split the full string at
once when that matters.

## API

- `split_graphemes(text: str) -> list[str]` — returns the extended grapheme
  clusters of `text`. The empty string returns an empty list.
- `GraphemeClusterSegmenter(text: str)` — a small object wrapper. It exposes
  `.text`, `.clusters`, `len(seg)`, and iteration over the clusters.
