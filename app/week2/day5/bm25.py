"""
Hand-built BM25 keyword scorer.

BM25 improves on raw term overlap by accounting for:
  1. Term frequency saturation (TF)      - a word appearing 10x isn't 10x more relevant
  2. Inverse document frequency (IDF)     - rare terms carry more signal
  3. Document length normalization        - long docs shouldn't win just for being long

Score(q, d) = sum over terms t in q of:
    IDF(t) * ( f(t,d) * (k1 + 1) ) / ( f(t,d) + k1 * (1 - b + b * |d|/avgdl) )

where f(t,d) is term frequency, |d| doc length, avgdl average doc length.
"""

import math
from collections import Counter


class BM25:
    """Okapi BM25 ranking function implemented from first principles."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1  # term-frequency saturation
        self.b = 0.75 if b is None else b  # length-normalization strength
        self.corpus: list[str] = []
        self.doc_tokens: list[list[str]] = []
        self.doc_len: list[int] = []
        self.avgdl: float = 0.0
        self.idf: dict[str, float] = {}

    def _tokenize(self, text: str) -> list[str]:
        """Lowercase alphanumeric tokenization."""
        return [
            t
            for t in "".join(c.lower() if c.isalnum() else " " for c in text).split()
            if t
        ]

    def fit(self, documents: list[str]) -> None:
        """Precompute document frequencies, lengths, and IDF for the corpus."""
        self.corpus = documents
        self.doc_tokens = [self._tokenize(d) for d in documents]
        self.doc_len = [len(toks) for toks in self.doc_tokens]
        self.avgdl = sum(self.doc_len) / len(self.doc_len) if self.doc_len else 0.0

        doc_freq: Counter = Counter()
        for toks in self.doc_tokens:
            for term in set(toks):
                doc_freq[term] += 1

        n = len(self.corpus)
        for term, df in doc_freq.items():
            # Robertson/Spark-Jones IDF (floored at 0 to avoid negative scores)
            self.idf[term] = max(0.0, math.log((n - df + 0.5) / (df + 0.5) + 1))

    def score(self, query: str, doc_index: int) -> float:
        """Compute the BM25 score of one document against the query."""
        query_terms = self._tokenize(query)
        doc_terms = self.doc_tokens[doc_index]
        tf = Counter(doc_terms)
        dl = self.doc_len[doc_index]

        score = 0.0
        for term in query_terms:
            if term not in self.idf:
                continue
            f = tf[term]
            numerator = f * (self.k1 + 1)
            denominator = f + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
            score += self.idf[term] * numerator / denominator
        return score

    def top_k(self, query: str, k: int = 10) -> list[tuple[int, float]]:
        """Return the top-k (doc_index, score) pairs for the query."""
        scored = [(i, self.score(query, i)) for i in range(len(self.corpus))]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]
