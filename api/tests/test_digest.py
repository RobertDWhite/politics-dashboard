import unittest

from app.services.digest import _safe_fallback, _validate_digest


ARTICLES = [
    {
        "source": "Official source",
        "title": "President Donald Trump announces a policy",
        "url": "https://example.test/policy",
        "content": "President Donald Trump announced a policy on Monday.",
        "published": 1,
    },
    {
        "source": "Congressional source",
        "title": "Congress considers a bill",
        "url": "https://example.test/bill",
        "content": "Lawmakers considered a bill during a committee hearing.",
        "published": 1,
    },
]


class DigestGroundingTests(unittest.TestCase):
    def test_accepts_cited_source_backed_digest(self):
        _validate_digest(
            "## Executive Branch\n"
            "- **Policy announcement** — President Donald Trump announced a policy. [S1]\n"
            "\n## Congress\n"
            "- **Committee hearing** — Lawmakers considered a bill. [S2]\n"
            "\n## Bottom Line\n"
            "Two current developments are covered.",
            ARTICLES,
        )

    def test_rejects_uncited_or_templated_output(self):
        with self.assertRaises(ValueError):
            _validate_digest(
                "## Executive Branch\n"
                "- **Headline phrase** — 1-2 sentence factual summary with key actors and outcome.\n"
                "- **Another item** — Summary.\n"
                "\n## Bottom Line\nSummary.",
                ARTICLES,
            )

    def test_rejects_unsupported_presidential_reference(self):
        with self.assertRaises(ValueError):
            _validate_digest(
                "## Executive Branch\n"
                "- **Veto decision** — President Joe Biden signed a bill. [S1]\n"
                "\n## Congress\n"
                "- **Committee hearing** — Lawmakers considered a bill. [S2]\n"
                "\n## Bottom Line\nSummary.",
                ARTICLES,
            )

    def test_accepts_rules_star_bullets_and_grouped_citations(self):
        _validate_digest(
            "## Executive Branch\n"
            "* **Policy announcement** — President Donald Trump announced a policy. [S1, S2]\n"
            "\n---\n"
            "## Congress\n"
            "- **Committee hearing** — Lawmakers considered a bill. [S2]\n"
            "\n## Bottom Line\n"
            "Two current developments are covered.",
            ARTICLES,
        )

    def test_accepts_title_cased_and_possessive_presidential_reference(self):
        _validate_digest(
            "## Executive Branch\n"
            "- **President Donald Trump Announces Policy** — President Donald Trump's policy was announced. [S1]\n"
            "\n## Congress\n"
            "- **Committee hearing** — Lawmakers considered a bill. [S2]\n"
            "\n## Bottom Line\n"
            "Two current developments are covered.",
            ARTICLES,
        )

    def test_accepts_single_bullet_when_only_one_source(self):
        _validate_digest(
            "## Executive Branch\n"
            "- **Policy announcement** — President Donald Trump announced a policy. [S1]\n"
            "\n## Bottom Line\n"
            "One current development is covered.",
            ARTICLES[:1],
        )

    def test_rejects_single_bullet_when_several_sources(self):
        with self.assertRaises(ValueError):
            _validate_digest(
                "## Executive Branch\n"
                "- **Policy announcement** — President Donald Trump announced a policy. [S1]\n"
                "\n## Bottom Line\n"
                "One current development is covered.",
                ARTICLES,
            )

    def test_rejects_grouped_citation_outside_evidence(self):
        with self.assertRaises(ValueError):
            _validate_digest(
                "## Executive Branch\n"
                "- **Policy announcement** — President Donald Trump announced a policy. [S1, S9]\n"
                "\n## Congress\n"
                "- **Committee hearing** — Lawmakers considered a bill. [S2]\n"
                "\n## Bottom Line\nSummary.",
                ARTICLES,
            )

    def test_fallback_is_cited(self):
        fallback = _safe_fallback(ARTICLES, "The AI model was unavailable.")
        self.assertIn("The AI model was unavailable.", fallback)
        _validate_digest(fallback, ARTICLES)


if __name__ == "__main__":
    unittest.main()

class StructuredDigestTests(unittest.TestCase):
    def test_excludes_corrupted_short_and_duplicate_sources(self):
        from app.services.digest import _select_evidence
        good = dict(ARTICLES[0], content='A usable source excerpt with enough factual detail to summarize accurately.')
        broken = dict(good, url='https://bad.test', title='[AI Error]')
        self.assertEqual(_select_evidence([broken, dict(good, title='[Summary] Feed roundup'), dict(good, content='AI Error: failed'), dict(good, content='short'), good, good]), [good])

    def test_rejects_invented_sentence_id(self):
        from app.services.digest import _parse_batch
        with self.assertRaises(ValueError):
            _parse_batch('{"items":[{"source_id":1,"sentence_id":99}]}', ARTICLES[:1])

    def test_requires_exact_source_ids(self):
        from app.services.digest import _parse_batch
        with self.assertRaises(ValueError):
            _parse_batch('{"items":[{"source_id":1,"sentence_id":1},{"source_id":1,"sentence_id":1}]}', ARTICLES)

    def test_accepts_fenced_json_and_returns_only_source_text(self):
        from app.services.digest import _parse_batch
        raw = '```json\n{"items":[{"source_id":2,"sentence_id":1},{"source_id":1,"sentence_id":1}]}\n```'
        self.assertEqual(_parse_batch(raw, ARTICLES), [a['content'] for a in ARTICLES])

    def test_does_not_split_us_abbreviation(self):
        from app.services.digest import _sentences
        article = dict(ARTICLES[0], content="The agency warned that U.S. personnel abroad face increased threats.")
        self.assertEqual(_sentences(article), [article['content']])
