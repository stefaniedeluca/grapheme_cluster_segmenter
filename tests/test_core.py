import unittest

from grapheme_cluster_segmenter import split_graphemes, GraphemeClusterSegmenter


class TestSplitGraphemes(unittest.TestCase):
    def test_empty_string(self):
        self.assertEqual(split_graphemes(""), [])

    def test_single_ascii(self):
        self.assertEqual(split_graphemes("a"), ["a"])

    def test_ascii_word(self):
        self.assertEqual(split_graphemes("hello"), ["h", "e", "l", "l", "o"])

    def test_combining_mark_stays_with_base(self):
        # 'e' followed by COMBINING ACUTE ACCENT (U+0301)
        self.assertEqual(split_graphemes("e\u0301"), ["e\u0301"])

    def test_multiple_combining_marks(self):
        # 'a' with acute and grave accents
        self.assertEqual(split_graphemes("a\u0301\u0300"), ["a\u0301\u0300"])

    def test_combining_mark_after_ascii_word(self):
        self.assertEqual(split_graphemes("ab\u0301"), ["a", "b\u0301"])

    def test_emoji_zwj_sequence(self):
        # Family emoji: woman + ZWJ + girl
        family = "\U0001F469\u200D\U0001F467"
        self.assertEqual(split_graphemes(family), [family])

    def test_emoji_zwj_sequence_with_skin_tone(self):
        # Woman with skin tone + ZWJ + girl
        seq = "\U0001F469\U0001F3FD\u200D\U0001F467"
        self.assertEqual(split_graphemes(seq), [seq])

    def test_regional_indicator_flag(self):
        # US flag: two regional indicators
        flag = "\U0001F1FA\U0001F1F8"
        self.assertEqual(split_graphemes(flag), [flag])

    def test_regional_indicator_run_of_three(self):
        # Three regional indicators: first two pair, third stands alone
        ri_a = "\U0001F1E6"
        ri_b = "\U0001F1E7"
        ri_c = "\U0001F1E8"
        self.assertEqual(split_graphemes(ri_a + ri_b + ri_c), [ri_a + ri_b, ri_c])

    def test_hangul_jamo_sequence(self):
        # Leading, vowel, trailing jamo form one syllable
        seq = "\u1100\u1161\u11A8"
        self.assertEqual(split_graphemes(seq), [seq])

    def test_prepend_attaches_to_following(self):
        # Arabic number sign followed by a digit
        self.assertEqual(split_graphemes("\u0600\u0661"), ["\u0600\u0661"])

    def test_control_breaks_cluster(self):
        self.assertEqual(split_graphemes("a\nb"), ["a", "\n", "b"])

    def test_crlf_is_one_cluster(self):
        self.assertEqual(split_graphemes("\r\n"), ["\r\n"])

    def test_zwj_sequence_without_pictographic_base(self):
        # ZWJ after a non-pictographic letter does not join the next letter
        self.assertEqual(split_graphemes("a\u200Db"), ["a\u200D", "b"])

    def test_spacing_mark(self):
        # Devanagari vowel sign AA is a spacing mark (Mc)
        self.assertEqual(split_graphemes("\u0915\u093E"), ["\u0915\u093E"])

    def test_mixed_text(self):
        text = "a\u0301\U0001F1FA\U0001F1F8\u1100\u1161"
        self.assertEqual(
            split_graphemes(text),
            ["a\u0301", "\U0001F1FA\U0001F1F8", "\u1100\u1161"],
        )


class TestGraphemeClusterSegmenter(unittest.TestCase):
    def test_clusters_property(self):
        seg = GraphemeClusterSegmenter("a\u0301b")
        self.assertEqual(seg.clusters, ["a\u0301", "b"])

    def test_text_property(self):
        seg = GraphemeClusterSegmenter("abc")
        self.assertEqual(seg.text, "abc")

    def test_len(self):
        seg = GraphemeClusterSegmenter("a\u0301b")
        self.assertEqual(len(seg), 2)

    def test_iter(self):
        seg = GraphemeClusterSegmenter("abc")
        self.assertEqual(list(seg), ["a", "b", "c"])

    def test_empty(self):
        seg = GraphemeClusterSegmenter("")
        self.assertEqual(seg.clusters, [])
        self.assertEqual(len(seg), 0)

    def test_repr(self):
        seg = GraphemeClusterSegmenter("ab")
        self.assertEqual(repr(seg), "GraphemeClusterSegmenter('ab')")


if __name__ == "__main__":
    unittest.main()
