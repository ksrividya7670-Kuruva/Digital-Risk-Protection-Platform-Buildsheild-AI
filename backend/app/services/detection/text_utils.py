"""
Lightweight deterministic text utilities for the detection engine.

All functions are pure (no side effects, no external calls).
No ML or heavy NLP dependencies — designed for ARM64 Windows compatibility.

Techniques used:
  - Case + punctuation normalization
  - Token overlap (Jaccard similarity)
  - Character n-gram similarity
  - Edit distance (pure Python)
  - Keyword/phrase matching
"""

import re
import unicodedata
from typing import Sequence


# ── Normalization ─────────────────────────────────────────────────────────────

def normalize_text(text: str) -> str:
    """
    Normalize text for comparison:
      - Unicode NFKC normalization (é → e, etc.)
      - Lowercase
      - Remove punctuation and special characters
      - Collapse whitespace
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)   # punctuation → space
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_username(username: str) -> str:
    """
    Normalize a username/handle for identity comparison.
    Strips @, underscores, hyphens, dots, and numbers.
    Result is the pure alphabetic core of the handle.
    """
    if not text_or_empty(username):
        return ""
    u = username.lower().lstrip("@")
    u = re.sub(r"[^a-z0-9]", "", u)
    return u


def text_or_empty(value: str | None) -> str:
    return (value or "").strip()


# ── Token-based similarity ─────────────────────────────────────────────────────

def tokenize(text: str) -> set[str]:
    """Split normalized text into a set of word tokens (min length 2)."""
    return {t for t in normalize_text(text).split() if len(t) >= 2}


def jaccard_similarity(a: str, b: str) -> float:
    """
    Token-level Jaccard similarity between two strings.
    J(A,B) = |A∩B| / |A∪B|

    Returns 0.0–1.0. Returns 0.0 if both strings are empty.
    """
    tokens_a = tokenize(a)
    tokens_b = tokenize(b)
    if not tokens_a and not tokens_b:
        return 0.0
    union = tokens_a | tokens_b
    if not union:
        return 0.0
    return len(tokens_a & tokens_b) / len(union)


def token_overlap_ratio(a: str, b: str) -> float:
    """
    What fraction of tokens in the shorter string appear in the longer string?
    Useful for detecting subset matches ("novabank support" vs "novabank").
    """
    tokens_a = tokenize(a)
    tokens_b = tokenize(b)
    if not tokens_a or not tokens_b:
        return 0.0
    shorter = tokens_a if len(tokens_a) <= len(tokens_b) else tokens_b
    longer = tokens_b if len(tokens_a) <= len(tokens_b) else tokens_a
    if not shorter:
        return 0.0
    return len(shorter & longer) / len(shorter)


# ── Edit distance ─────────────────────────────────────────────────────────────

def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Pure Python Levenshtein edit distance.
    O(len(s1) * len(s2)) — acceptable for short strings (usernames, handles).
    """
    if s1 == s2:
        return 0
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)

    # Use two rows to save memory
    prev = list(range(len(s2) + 1))
    curr = [0] * (len(s2) + 1)

    for i, c1 in enumerate(s1, 1):
        curr[0] = i
        for j, c2 in enumerate(s2, 1):
            cost = 0 if c1 == c2 else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev, curr = curr, prev

    return prev[len(s2)]


def normalized_edit_similarity(s1: str, s2: str) -> float:
    """
    Edit distance similarity normalized to 0.0–1.0.
    1.0 = identical, 0.0 = completely different.
    """
    if not s1 and not s2:
        return 0.0
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 0.0
    dist = levenshtein_distance(s1, s2)
    return 1.0 - (dist / max_len)


# ── Character n-grams ─────────────────────────────────────────────────────────

def char_ngrams(text: str, n: int = 3) -> set[str]:
    """Extract character n-grams from text."""
    clean = normalize_text(text).replace(" ", "")
    if len(clean) < n:
        return {clean} if clean else set()
    return {clean[i:i+n] for i in range(len(clean) - n + 1)}


def ngram_similarity(a: str, b: str, n: int = 3) -> float:
    """Character n-gram Jaccard similarity."""
    ng_a = char_ngrams(a, n)
    ng_b = char_ngrams(b, n)
    if not ng_a and not ng_b:
        return 0.0
    union = ng_a | ng_b
    if not union:
        return 0.0
    return len(ng_a & ng_b) / len(union)


# ── Combined string similarity ─────────────────────────────────────────────────

def string_similarity(a: str, b: str) -> float:
    """
    Combines edit distance + token overlap + n-gram similarity
    into a single 0.0–1.0 score. Weighted average.

    Best for short strings like usernames and display names.
    """
    if not a or not b:
        return 0.0
    a_norm = normalize_username(a)
    b_norm = normalize_username(b)

    edit_sim = normalized_edit_similarity(a_norm, b_norm)
    token_sim = token_overlap_ratio(a, b)
    ngram_sim = ngram_similarity(a_norm, b_norm, n=2)

    return round(0.5 * edit_sim + 0.3 * token_sim + 0.2 * ngram_sim, 4)


# ── Keyword matching ──────────────────────────────────────────────────────────

# Terms that impersonators commonly use to appear official
SUSPICIOUS_CLAIM_TERMS: list[str] = [
    "official", "support", "help", "helpdesk", "customer care",
    "verified", "verification", "real", "genuine", "authentic",
    "service", "account", "team", "staff", "representative",
    "scholarship", "admission", "apply", "winner",
]

# Common suffix/prefix patterns used in impersonation
IMPERSONATION_AFFIXES: list[str] = [
    "official", "support", "help", "real", "genuine",
    "care", "service", "team", "hq", "global", "intl",
    "india", "usa", "uk", "ng", "gh", "za",          # geo suffixes
    "secure", "safe", "verify", "verified",
    "backup", "news", "updates", "alert", "alerts",
]


def contains_suspicious_claims(text: str) -> tuple[bool, list[str]]:
    """
    Check if text contains terms that impersonators use to appear official.
    Returns (found: bool, matched_terms: list[str]).
    """
    if not text:
        return False, []
    text_lower = text.lower()
    matched = [term for term in SUSPICIOUS_CLAIM_TERMS if term in text_lower]
    return bool(matched), matched


def has_impersonation_affix(candidate: str, brand: str) -> tuple[bool, str]:
    """
    Check if candidate username = brand_name + known_impersonation_affix
    or known_impersonation_affix + brand_name.

    Returns (found: bool, matched_affix: str)
    """
    c = normalize_username(candidate)
    b = normalize_username(brand)
    if not c or not b:
        return False, ""
    for affix in IMPERSONATION_AFFIXES:
        if c == b + affix or c == affix + b:
            return True, affix
        # Also check with brand name embedded
        if b in c and affix in c:
            return True, affix
    return False, ""


def keyword_overlap_score(text: str, keywords: list[str]) -> float:
    """
    What fraction of the given keywords appear in text?
    Returns 0.0–1.0.
    """
    if not text or not keywords:
        return 0.0
    text_lower = text.lower()
    matched = sum(1 for kw in keywords if kw.lower() in text_lower)
    return matched / len(keywords)
