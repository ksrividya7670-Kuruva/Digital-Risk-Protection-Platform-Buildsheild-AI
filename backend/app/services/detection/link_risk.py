"""
Signal 4 — Link / Contact Risk (weight: 15%)

Deterministic analysis of URLs, domains, and contact information.
No external HTTP requests are made — purely structural analysis of
provided string data.

Checks:
  - Domain mismatch (official domain vs candidate website domain)
  - Lookalike domain (brand name in domain but wrong TLD or with additions)
  - Suspicious URL patterns (obfuscation, URL shorteners, typosquatting)
  - Developer/contact email mismatch
  - Package name brand-squatting (for MOBILE_APP candidates)
  - Suspicious keywords in URL path
"""

from __future__ import annotations
import re

from app.services.detection.contracts import SignalResult, SIGNAL_WEIGHTS
from app.services.detection.text_utils import (
    normalize_username,
    text_or_empty,
    string_similarity,
)

SIGNAL_NAME = "link_risk"
WEIGHT = SIGNAL_WEIGHTS[SIGNAL_NAME]

# Free / suspicious URL shorteners
_URL_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "ow.ly", "buff.ly",
    "goo.gl", "short.link", "rb.gy", "cutt.ly", "tiny.cc",
}

# Suspicious TLDs often used in phishing
_SUSPICIOUS_TLDS = {
    ".xyz", ".tk", ".ml", ".ga", ".cf", ".gq", ".pw",
    ".top", ".click", ".link", ".info", ".biz",
}

# Suspicious keywords in URLs or package names
_SUSPICIOUS_URL_KEYWORDS = [
    "secure", "official", "support", "help", "verify",
    "login", "signin", "account", "update", "free",
    "winner", "claim", "prize", "reward",
]

# Suspicious email domains (free providers used to fake support emails)
_FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "protonmail.com", "mail.com", "icloud.com", "aol.com",
    "yandex.com", "tutanota.com",
}


def _extract_domain(url: str) -> str:
    """
    Extract the registrable domain from a URL or email address.
    Pure string parsing — no DNS lookup.

    Examples:
      "https://novabank-secure.com/support" → "novabank-secure.com"
      "support@novabank-secure.com"         → "novabank-secure.com"
    """
    if not url:
        return ""
    url = url.lower().strip()
    # Handle email
    if "@" in url and "/" not in url:
        return url.split("@")[-1]
    # Strip scheme
    url = re.sub(r"^https?://", "", url)
    url = re.sub(r"^www\.", "", url)
    # Take up to first slash (path) or colon (port)
    domain = re.split(r"[/?:#]", url)[0]
    return domain.strip()


def _domain_is_official(domain: str, official_domain: str) -> bool:
    """Returns True if the candidate domain matches the official domain exactly."""
    if not domain or not official_domain:
        return False
    return domain.strip("/").lower() == official_domain.strip("/").lower()


def _has_suspicious_tld(domain: str) -> tuple[bool, str]:
    for tld in _SUSPICIOUS_TLDS:
        if domain.endswith(tld):
            return True, tld
    return False, ""


def _is_lookalike_domain(domain: str, brand_name: str, official_domain: str) -> bool:
    """
    Returns True if the domain contains the brand name but is NOT the
    official domain — a classic lookalike pattern.
    """
    b = normalize_username(brand_name)
    d_clean = normalize_username(domain)
    off_clean = normalize_username(official_domain)
    if not b or not d_clean:
        return False
    return (b in d_clean) and (d_clean != off_clean)


def calculate(
    *,
    brand_name: str,
    official_domain: str | None,
    official_developer_name: str | None,
    official_email_domain: str | None,
    # Candidate fields
    candidate_website: str | None,
    candidate_email: str | None,
    candidate_package_name: str | None,      # MOBILE_APP only
    candidate_developer_name: str | None,    # MOBILE_APP only
    candidate_developer_email: str | None,   # MOBILE_APP only
) -> SignalResult:
    """
    Calculate link/contact risk for a candidate.
    All analysis is structural — no HTTP requests.
    """
    reasons: list[str] = []
    metadata: dict = {}
    risk_components: list[float] = []

    b_name   = text_or_empty(brand_name)
    off_dom  = text_or_empty(official_domain)
    off_edom = text_or_empty(official_email_domain) or off_dom

    # ── 1. Website / profile URL analysis ─────────────────────────────────────
    if candidate_website:
        c_domain = _extract_domain(candidate_website)
        metadata["candidate_domain"] = c_domain

        if off_dom:
            if _domain_is_official(c_domain, off_dom):
                # Good — matches official domain, reduces risk
                metadata["domain_matches_official"] = True
                reasons.append(f"Candidate website matches official domain '{off_dom}'.")
                risk_components.append(0.0)
            else:
                metadata["domain_matches_official"] = False
                risk_components.append(0.60)  # domain mismatch base risk

                # Lookalike?
                if _is_lookalike_domain(c_domain, b_name, off_dom):
                    metadata["lookalike_domain"] = True
                    reasons.append(
                        f"Candidate uses a lookalike domain '{c_domain}' that contains "
                        f"the brand name but is NOT the official domain '{off_dom}'."
                    )
                    risk_components.append(0.85)
                else:
                    reasons.append(
                        f"Candidate website domain '{c_domain}' does not match "
                        f"official domain '{off_dom}'."
                    )

                # Suspicious TLD?
                has_tld, tld = _has_suspicious_tld(c_domain)
                if has_tld:
                    metadata["suspicious_tld"] = tld
                    reasons.append(
                        f"Candidate domain uses suspicious TLD '{tld}'."
                    )
                    risk_components.append(0.70)

        # URL shortener?
        if any(shortener in (candidate_website or "") for shortener in _URL_SHORTENERS):
            metadata["url_shortener"] = True
            reasons.append("Candidate profile uses a URL shortener — destination unknown.")
            risk_components.append(0.50)

        # Suspicious keywords in URL?
        kw_found = [
            kw for kw in _SUSPICIOUS_URL_KEYWORDS
            if kw in (candidate_website or "").lower()
        ]
        # Don't flag keyword risk if this is the official domain
        if kw_found and off_dom and _domain_is_official(c_domain, off_dom):
            kw_found = []  # official domain paths are not suspicious
        if kw_found:
            metadata["suspicious_url_keywords"] = kw_found
            reasons.append(
                f"Candidate URL contains suspicious keywords: {', '.join(kw_found)}."
            )
            risk_components.append(0.40)

    # ── 2. Contact email analysis ──────────────────────────────────────────────
    if candidate_email:
        email_domain = _extract_domain(candidate_email)
        metadata["candidate_email_domain"] = email_domain

        if off_edom and email_domain:
            if email_domain == off_edom:
                metadata["email_matches_official"] = True
                # Matching email domain reduces risk slightly
                risk_components.append(0.0)
            else:
                if email_domain in _FREE_EMAIL_DOMAINS:
                    reasons.append(
                        f"Candidate uses a free email provider '{email_domain}' "
                        f"instead of the official domain '{off_edom}'."
                    )
                    risk_components.append(0.55)
                elif _is_lookalike_domain(email_domain, b_name, off_edom):
                    reasons.append(
                        f"Contact email uses a lookalike domain '{email_domain}'."
                    )
                    risk_components.append(0.80)
                else:
                    reasons.append(
                        f"Contact email domain '{email_domain}' does not match "
                        f"official email domain '{off_edom}'."
                    )
                    risk_components.append(0.45)

    # ── 3. Mobile app — package name analysis ─────────────────────────────────
    if candidate_package_name:
        pkg = candidate_package_name.lower()
        b_norm = normalize_username(b_name)
        if b_norm and b_norm in pkg:
            metadata["brand_in_package"] = True
            reasons.append(
                f"App package name '{candidate_package_name}' contains the brand name."
            )
            risk_components.append(0.50)

            # If developer doesn't match official, that's a red flag
            if official_developer_name and candidate_developer_name:
                dev_sim = string_similarity(official_developer_name, candidate_developer_name)
                metadata["developer_similarity"] = round(dev_sim, 3)
                if dev_sim < 0.50:
                    reasons.append(
                        f"Developer '{candidate_developer_name}' does not match "
                        f"official developer '{official_developer_name}'."
                    )
                    risk_components.append(0.75)

        if candidate_developer_email:
            dev_email_domain = _extract_domain(candidate_developer_email)
            if dev_email_domain in _FREE_EMAIL_DOMAINS:
                reasons.append(
                    f"App developer uses a free email provider '{dev_email_domain}' "
                    f"— legitimate publishers use corporate emails."
                )
                risk_components.append(0.60)

    # ── Combine ───────────────────────────────────────────────────────────────
    if not risk_components:
        return SignalResult(
            signal_name=SIGNAL_NAME,
            raw_score=0.0,
            weight=WEIGHT,
            weighted_score=0.0,
            reason="No URL, domain, or contact information available for analysis.",
            metadata=metadata,
        )

    # Take the maximum risk component (worst-case URL risk dominates)
    raw_score = round(min(1.0, max(risk_components)), 4)

    if not reasons:
        reasons.append("No significant link or contact risk signals detected.")

    return SignalResult(
        signal_name=SIGNAL_NAME,
        raw_score=raw_score,
        weight=WEIGHT,
        weighted_score=round(raw_score * WEIGHT, 4),
        reason="; ".join(reasons),
        metadata=metadata,
    )
