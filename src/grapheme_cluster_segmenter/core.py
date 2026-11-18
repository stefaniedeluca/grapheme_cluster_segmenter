"""Grapheme cluster segmentation following Unicode Standard Annex #29.

This module implements a practical subset of the extended grapheme cluster
boundary rules. It handles combining marks, spacing marks, the Hangul syllable
jamo sequences, regional indicator pairs, prepend characters, and ZWJ emoji
sequences. It does not implement every table-driven rule from the full
specification; the goal is to cover the cases that appear in real text and in
the project test suite.

The segmentation is done by scanning code points and applying boundary rules
between adjacent code points. A cluster is a maximal run of code points with no
boundary between them.
"""

from __future__ import annotations

import unicodedata
from typing import List

__all__ = ["split_graphemes", "GraphemeClusterSegmenter"]


def _is_extend(cp: int) -> bool:
    """Return True if the code point is a combining mark or similar extender.

    Extend includes the general categories Mn (nonspacing mark), Me (enclosing
    mark) and most of Mc (spacing combining mark), plus a handful of format
    characters that attach to the previous character. We use the Unicode
    category as the primary signal because it is available in the standard
    library and is stable for the code points we care about.
    """
    cat = unicodedata.category(chr(cp))
    if cat in ("Mn", "Me", "Mc"):
        return True
    # ZWJ and ZWNJ are format characters that behave as extenders for the
    # purpose of keeping a cluster together. The variation selectors are also
    # format characters that must attach to the base character.
    if cp in (0x200C, 0x200D):
        return True
    if 0xFE00 <= cp <= 0xFE0F:
        return True
    if 0xE0100 <= cp <= 0xE01EF:
        return True
    if 0x1F3FB <= cp <= 0x1F3FF:
        return True
    return False


def _is_spacing_mark(cp: int) -> bool:
    """Return True for spacing combining marks (category Mc).

    Rule GB9a says a spacing mark attaches to the previous cluster. We treat
    Mc separately from other extenders only where the distinction matters; in
    this implementation both attach, so this helper exists for clarity.
    """
    return unicodedata.category(chr(cp)) == "Mc"


def _is_prepend(cp: int) -> bool:
    """Return True for prepend characters (rule GB9b).

    Prepend characters attach to the following character rather than the
    previous one. The main examples are Arabic number signs and the Syriac
    abbreviation mark.
    """
    return cp in (0x0600, 0x0601, 0x0602, 0x0603, 0x0604, 0x0605, 0x06DD, 0x070F, 0x08E2, 0x110BD, 0x110CD)


def _is_hangul_l(cp: int) -> bool:
    """Hangul syllable type L (leading jamo)."""
    return 0x1100 <= cp <= 0x115F or 0xA960 <= cp <= 0xA97C


def _is_hangul_v(cp: int) -> bool:
    """Hangul syllable type V (vowel jamo)."""
    return 0x1160 <= cp <= 0x11A7 or 0xD7B0 <= cp <= 0xD7C6


def _is_hangul_t(cp: int) -> bool:
    """Hangul syllable type T (trailing jamo)."""
    return 0x11A8 <= cp <= 0x11FF or 0xD7CB <= cp <= 0xD7FB


def _is_hangul_lv(cp: int) -> bool:
    """Hangul syllable type LV (precomposed syllable with leading+vowel)."""
    if not (0xAC00 <= cp <= 0xD7A3):
        return False
    return (cp - 0xAC00) % 28 == 0


def _is_hangul_lvt(cp: int) -> bool:
    """Hangul syllable type LVT (precomposed syllable with trailing)."""
    if not (0xAC00 <= cp <= 0xD7A3):
        return False
    return (cp - 0xAC00) % 28 != 0


def _is_regional_indicator(cp: int) -> bool:
    """Regional indicator symbols used in flag sequences."""
    return 0x1F1E6 <= cp <= 0x1F1FF


def _is_zwj(cp: int) -> bool:
    """Zero width joiner."""
    return cp == 0x200D


def _is_extended_pictographic(cp: int) -> bool:
    """Return True for code points with the Extended_Pictographic property.

    Python's unicodedata does not expose this property directly. We use the
    emoji ranges defined by Unicode plus the Misc Symbols and Dingbats blocks,
    which cover the pictographic characters that participate in ZWJ sequences.
    This is a deliberate approximation: it is correct for the sequences we
    test and for the common emoji in wide use.
    """
    if 0x1F300 <= cp <= 0x1F5FF:
        return True
    if 0x1F600 <= cp <= 0x1F64F:
        return True
    if 0x1F680 <= cp <= 0x1F6FF:
        return True
    if 0x1F900 <= cp <= 0x1F9FF:
        return True
    if 0x1FA70 <= cp <= 0x1FAFF:
        return True
    if 0x2600 <= cp <= 0x27BF:
        return True
    if 0x2B00 <= cp <= 0x2BFF:
        return True
    if 0x1F000 <= cp <= 0x1F02F:
        return True
    if 0x1F0A0 <= cp <= 0x1F0FF:
        return True
    if 0x1F100 <= cp <= 0x1F1AD:
        return True
    if 0x1F200 <= cp <= 0x1F2FF:
        return True
    if 0x1F700 <= cp <= 0x1F77F:
        return True
    if 0x1F780 <= cp <= 0x1F7FF:
        return True
    if 0x1F800 <= cp <= 0x1F8FF:
        return True
    return False


def _is_control(cp: int) -> bool:
    """Control characters break clusters (rules GB4, GB5)."""
    return unicodedata.category(chr(cp)) in ("Cc", "Cf", "Cs", "Co", "Cn") and cp not in (0x200C, 0x200D)


def _should_break(prev: int, curr: int, ri_run: int) -> bool:
    """Decide whether a grapheme cluster boundary exists between two code points.

    `prev` and `curr` are code points (ints). `ri_run` is the number of
    consecutive regional indicators immediately before `curr` in the current
    cluster. It is used to pair regional indicators two at a time (rule GB12).
    """
    # GB3: CR x LF
    if prev == 0x0D and curr == 0x0A:
        return False
    # GB4: break after controls, CR, LF
    if _is_control(prev) or prev in (0x0D, 0x0A):
        return True
    # GB5: break before controls, CR, LF
    if _is_control(curr) or curr in (0x0D, 0x0A):
        return True
    # GB6: L x (L | V | LV | LVT)
    if _is_hangul_l(prev) and (_is_hangul_l(curr) or _is_hangul_v(curr) or _is_hangul_lv(curr) or _is_hangul_lvt(curr)):
        return False
    # GB7: (LV | V) x (V | T)
    if (_is_hangul_lv(prev) or _is_hangul_v(prev)) and (_is_hangul_v(curr) or _is_hangul_t(curr)):
        return False
    # GB8: (LVT | T) x T
    if (_is_hangul_lvt(prev) or _is_hangul_t(prev)) and _is_hangul_t(curr):
        return False
    # GB9: x (Extend | ZWJ)
    if _is_extend(curr):
        return False
    # GB9a: x SpacingMark
    if _is_spacing_mark(curr):
        return False
    # GB9b: Prepend x
    if _is_prepend(prev):
        return False
    # GB11: ExtPict Extend* ZWJ x ExtPict
    if _is_zwj(prev) and _is_extended_pictographic(curr):
        return False
    # GB12/GB13: regional indicators pair up
    if _is_regional_indicator(prev) and _is_regional_indicator(curr):
        # If the run of regional indicators before curr is odd, pair them.
        return ri_run % 2 == 0
    # GB999: break everywhere else
    return True


def split_graphemes(text: str) -> List[str]:
    """Split `text` into a list of extended grapheme clusters.

    Each returned element is a string containing one user-perceived character.
    The empty string returns an empty list. The function is pure and does not
    depend on locale or on any external data files.
    """
    if not text:
        return []
    cps = [ord(ch) for ch in text]
    clusters: List[str] = []
    current: List[int] = [cps[0]]
    ri_run = 1 if _is_regional_indicator(cps[0]) else 0
    prepend_pending = _is_prepend(cps[0])
    for i in range(1, len(cps)):
        prev = cps[i - 1]
        curr = cps[i]
        if not prepend_pending and _should_break(prev, curr, ri_run):
            clusters.append("".join(chr(c) for c in current))
            current = [curr]
            ri_run = 1 if _is_regional_indicator(curr) else 0
            prepend_pending = _is_prepend(curr)
        else:
            current.append(curr)
            if _is_regional_indicator(curr):
                ri_run += 1
            else:
                ri_run = 0
            prepend_pending = _is_prepend(curr)
    clusters.append("".join(chr(c) for c in current))
    return clusters


class GraphemeClusterSegmenter:
    """Reusable segmenter object.

    The segmentation logic is stateless, so this class exists mainly as a
    convenience for callers that prefer an object-oriented API or that want to
    cache the result of a split. It stores the original string and the computed
    clusters.
    """

    def __init__(self, text: str) -> None:
        self._text = text
        self._clusters = split_graphemes(text)

    @property
    def text(self) -> str:
        """The original string passed to the constructor."""
        return self._text

    @property
    def clusters(self) -> List[str]:
        """The grapheme clusters of the original string."""
        return list(self._clusters)

    def __len__(self) -> int:
        return len(self._clusters)

    def __iter__(self):
        return iter(self._clusters)

    def __repr__(self) -> str:
        return f"GraphemeClusterSegmenter({self._text!r})"
