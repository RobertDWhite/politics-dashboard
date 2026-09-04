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

    def test_fallback_is_cited(self):
        fallback = _safe_fallback(ARTICLES)
        _validate_digest(fallback, ARTICLES)


if __name__ == "__main__":
    unittest.main()
