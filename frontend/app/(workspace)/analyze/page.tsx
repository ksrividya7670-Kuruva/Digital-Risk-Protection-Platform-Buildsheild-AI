"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, ApiError, type Candidate, type RiskLevel } from "@/lib/api";
import { notify } from "@/lib/ui";
import { PageHeading, Panel, RiskBadge } from "@/components/ui";

/* ─── types ─── */
interface AnalysisSignal { name: string; score: number; explanation: string; }
interface AnalysisResult {
  entity_type: "NAME" | "SOCIAL_PROFILE" | "WEBSITE" | "MOBILE_APP";
  entity_label: string;
  risk_score: number;
  risk_level: RiskLevel;
  signals: AnalysisSignal[];
  explanation: string;
  recommended_action: string;
  generated_at: string;
}

/* ─── deterministic helpers ─── */
function toLevel(score: number): RiskLevel {
  if (score >= 80) return "CRITICAL";
  if (score >= 60) return "HIGH";
  if (score >= 40) return "MEDIUM";
  return "LOW";
}

function analyzeNameLogic(name: string): AnalysisResult {
  const signals: AnalysisSignal[] = [];
  let score = 10;
  const n = name.toLowerCase();
  const FINANCIAL = ['pay', 'bank', 'crypto', 'wallet', 'finance', 'invest', 'coin'];
  const AUTH_WORDS = ['official', 'verify', 'secure', 'support', 'admin', 'real'];
  const KNOWN = ['apple', 'google', 'microsoft', 'amazon', 'facebook', 'instagram', 'whatsapp', 'paypal', 'visa', 'mastercard', 'novapay'];
  if (FINANCIAL.some(k => n.includes(k))) {
    score += 28; signals.push({ name: "Financial Keyword", score: 28, explanation: "Name contains a financial keyword commonly used in payment impersonation attacks." });
  }
  if (AUTH_WORDS.some(k => n.includes(k))) {
    score += 32; signals.push({ name: "Authority Claim", score: 32, explanation: "Name claims official, verified or administrative status — a hallmark of impersonation." });
  }
  const match = KNOWN.find(b => n.includes(b) || levenshtein(n, b) <= 2);
  if (match) {
    score += 38; signals.push({ name: "Brand Similarity", score: 38, explanation: `High similarity to protected brand "${match}" — possible impersonation attempt.` });
  }
  if (/[0-9]/.test(name) || /[_\-]{2,}/.test(name)) {
    score += 18; signals.push({ name: "Character Substitution", score: 18, explanation: "Numbers or repeated separators suggest typosquatting or character substitution." });
  }
  const final = Math.min(100, score);
  const level = toLevel(final);
  return {
    entity_type: "NAME", entity_label: name,
    risk_score: final, risk_level: level, signals,
    explanation: `Brand name analysis for "${name}" completed. The deterministic engine evaluated ${signals.length} risk signal${signals.length !== 1 ? "s" : ""} including keyword patterns, similarity to protected brands, and character substitution indicators.`,
    recommended_action: level === "CRITICAL" || level === "HIGH" ? "Open an investigation case immediately and validate brand ownership." : level === "MEDIUM" ? "Queue for analyst review — monitor for escalation." : "No immediate action required. Continue passive monitoring.",
    generated_at: new Date().toISOString(),
  };
}

function analyzeSocialLogic(platform: string, username: string, displayName: string, bio: string, website: string): AnalysisResult {
  const signals: AnalysisSignal[] = [];
  let score = 12;
  const u = (username || displayName).toLowerCase();
  const SUSPICIOUS_PATTERNS = ['official', 'verified', 'real', 'support', 'admin', 'help', 'customer'];
  if (SUSPICIOUS_PATTERNS.some(p => u.includes(p))) {
    score += 35; signals.push({ name: "Suspicious Username", score: 35, explanation: "Username contains authority or verification claims — strong impersonation indicator." });
  }
  if (/\d{4,}/.test(u) || u.split(/[._\-]/).length > 4) {
    score += 22; signals.push({ name: "Username Anomaly", score: 22, explanation: "Username pattern (excessive numbers or separators) is consistent with auto-generated accounts." });
  }
  if (bio) {
    const SCAM_PHRASES = ['dm for', 'click link', 'limited time', 'act now', 'verify account', 'customer service', 'win prize', 'free gift'];
    if (SCAM_PHRASES.some(p => bio.toLowerCase().includes(p))) {
      score += 30; signals.push({ name: "Suspicious Bio Content", score: 30, explanation: "Bio contains language patterns associated with scam or phishing profiles." });
    }
  }
  if (website) {
    if (!website.startsWith('https://')) {
      score += 18; signals.push({ name: "Insecure External Link", score: 18, explanation: "Profile links to an HTTP (unencrypted) site — common in phishing profiles." });
    }
    const SUSPECT_TLDS = ['.tk', '.ml', '.ga', '.cf', '.xyz', '.top', '.click'];
    if (SUSPECT_TLDS.some(t => website.includes(t))) {
      score += 22; signals.push({ name: "Suspicious Link Domain", score: 22, explanation: "External link uses a TLD frequently associated with throwaway phishing sites." });
    }
  }
  const final = Math.min(100, score);
  const label = username ? `@${username.replace(/^@/, '')} (${platform})` : `${displayName} (${platform})`;
  return {
    entity_type: "SOCIAL_PROFILE", entity_label: label,
    risk_score: final, risk_level: toLevel(final), signals,
    explanation: `Social profile analysis for ${label} identified ${signals.length} risk indicator${signals.length !== 1 ? "s" : ""}. Assessment is based on username patterns, bio content analysis, and external link reputation. This is a synthetic deterministic analysis.`,
    recommended_action: toLevel(final) === "CRITICAL" || toLevel(final) === "HIGH" ? "Flag account for platform takedown and open investigation case." : toLevel(final) === "MEDIUM" ? "Flag for analyst review. Monitor bio and link changes." : "No immediate action. Log for passive monitoring.",
    generated_at: new Date().toISOString(),
  };
}

function analyzeWebsiteLogic(url: string): AnalysisResult {
  const signals: AnalysisSignal[] = [];
  let score = 8;
  let domain = url;
  try {
    domain = new URL(url.startsWith('http') ? url : `https://${url}`).hostname.toLowerCase();
  } catch { /* keep raw */ }
  const SUSPECT_TLDS = ['.tk', '.ml', '.ga', '.cf', '.click', '.top', '.xyz', '.site', '.pw'];
  if (SUSPECT_TLDS.some(t => domain.endsWith(t))) {
    score += 40; signals.push({ name: "Suspicious TLD", score: 40, explanation: "Top-level domain is associated with free or throwaway registrations used in phishing." });
  }
  const LOOKALIKES = [['g00gle', 'google'], ['app1e', 'apple'], ['micr0soft', 'microsoft'], ['amaz0n', 'amazon'], ['paypa1', 'paypal'], ['faceb00k', 'facebook'], ['novapay', 'novapay']];
  const hit = LOOKALIKES.find(([lk]) => domain.includes(lk));
  if (hit) {
    score += 50; signals.push({ name: "Brand Lookalike Domain", score: 50, explanation: `Domain "${domain}" contains a character-substituted variant of "${hit[1]}" — high-confidence typosquatting.` });
  }
  const parts = domain.replace(/^www\./, '').split('.');
  if (parts.length > 4) {
    score += 24; signals.push({ name: "Excessive Subdomains", score: 24, explanation: "Deeply nested subdomains are used to create misleadingly long URLs that obscure the real domain." });
  }
  if (!url.toLowerCase().startsWith('https://')) {
    score += 28; signals.push({ name: "No HTTPS", score: 28, explanation: "Site lacks TLS/HTTPS. Credentials and data transmitted in plaintext." });
  }
  const SUSPECT_KEYWORDS = ['secure', 'verify', 'login', 'account', 'update', 'support'];
  if (SUSPECT_KEYWORDS.some(k => domain.includes(k))) {
    score += 20; signals.push({ name: "Phishing Keyword in Domain", score: 20, explanation: "Domain contains a keyword (secure, verify, login, etc.) associated with credential phishing." });
  }
  const final = Math.min(100, score);
  return {
    entity_type: "WEBSITE", entity_label: domain,
    risk_score: final, risk_level: toLevel(final), signals,
    explanation: `URL analysis for "${domain}" completed. The deterministic engine evaluated ${signals.length} signal${signals.length !== 1 ? "s" : ""} against domain structure, TLD reputation, and keyword patterns. No live web request was made — this is a safe local pattern analysis.`,
    recommended_action: toLevel(final) === "CRITICAL" || toLevel(final) === "HIGH" ? "Block domain and submit for takedown. Open investigation case immediately." : toLevel(final) === "MEDIUM" ? "Investigate domain registration details. Monitor for credential phishing activity." : "Low risk. Continue routine monitoring.",
    generated_at: new Date().toISOString(),
  };
}

function analyzeAppLogic(appName: string, packageId: string, appPlatform: string, developerName: string): AnalysisResult {
  const signals: AnalysisSignal[] = [];
  let score = 18;
  const n = appName.toLowerCase();
  const AUTHORITY_WORDS = ['official', 'premium', 'pro', 'plus', 'verified', 'secure', 'real', 'original'];
  if (AUTHORITY_WORDS.some(k => n.includes(k))) {
    score += 32; signals.push({ name: "Authority Claim in App Name", score: 32, explanation: "App name includes authority or premium claims (official, verified, premium) without evidence of legitimacy." });
  }
  const BRAND_TRIGGER = ['whatsapp', 'instagram', 'facebook', 'gmail', 'chrome', 'outlook', 'office', 'novapay'];
  const brandMatch = BRAND_TRIGGER.find(b => n.includes(b));
  if (brandMatch) {
    const KNOWN_DEVS: Record<string, string> = { whatsapp: 'meta', instagram: 'meta', facebook: 'meta', gmail: 'google', chrome: 'google', outlook: 'microsoft', office: 'microsoft', novapay: 'novapay' };
    const expectedDev = KNOWN_DEVS[brandMatch];
    if (developerName && expectedDev && !developerName.toLowerCase().includes(expectedDev)) {
      score += 42; signals.push({ name: "Developer Identity Mismatch", score: 42, explanation: `App name references "${brandMatch}" but developer "${developerName}" does not match expected developer "${expectedDev}". High-confidence impersonation indicator.` });
    } else if (!developerName) {
      score += 20; signals.push({ name: "No Developer Identity", score: 20, explanation: `App name references a known brand "${brandMatch}" but no developer name was provided for verification.` });
    }
  }
  if (packageId) {
    const KNOWN_PACKAGES = ['com.google', 'com.meta', 'com.facebook', 'com.instagram', 'com.whatsapp', 'com.microsoft', 'com.apple'];
    if (KNOWN_PACKAGES.some(p => packageId.toLowerCase().startsWith(p)) && !KNOWN_PACKAGES.includes(packageId.toLowerCase())) {
      score += 44; signals.push({ name: "Package ID Spoofing", score: 44, explanation: `Package "${packageId}" mimics a trusted namespace but is not the official package. Classic side-loaded malware pattern.` });
    }
    if (packageId.split('.').length < 3) {
      score += 22; signals.push({ name: "Malformed Package ID", score: 22, explanation: "Package ID does not follow standard reverse-domain naming. Unusual for legitimate store apps." });
    }
  }
  const final = Math.min(100, score);
  return {
    entity_type: "MOBILE_APP", entity_label: `${appName} (${appPlatform})`,
    risk_score: final, risk_level: toLevel(final), signals,
    explanation: `Mobile app analysis for "${appName}" on ${appPlatform} completed. ${signals.length} risk signal${signals.length !== 1 ? "s" : ""} detected. Analysis covers app naming, package structure, and developer identity verification. This is a synthetic deterministic analysis — no live app store connection was made.`,
    recommended_action: toLevel(final) === "CRITICAL" || toLevel(final) === "HIGH" ? "Submit takedown request to app store. Open investigation case immediately." : toLevel(final) === "MEDIUM" ? "Flag for store review. Verify developer identity and permissions." : "Monitor for suspicious updates or user reports.",
    generated_at: new Date().toISOString(),
  };
}

/* Simple Levenshtein distance for brand similarity */
function levenshtein(a: string, b: string): number {
  const m = a.length, n = b.length;
  const dp: number[][] = Array.from({ length: m + 1 }, (_, i) => Array.from({ length: n + 1 }, (_, j) => (i === 0 ? j : j === 0 ? i : 0)));
  for (let i = 1; i <= m; i++) for (let j = 1; j <= n; j++) dp[i][j] = a[i-1] === b[j-1] ? dp[i-1][j-1] : 1 + Math.min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1]);
  return dp[m][n];
}

/* ─── component ─── */
export default function AnalyzePage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"name" | "social" | "website" | "app">("name");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState("");
  const [creatingCase, setCreatingCase] = useState(false);

  /* form state */
  const [brandName, setBrandName] = useState("");
  const [platform, setPlatform] = useState("Instagram");
  const [username, setUsername] = useState("");
  const [dispName, setDispName] = useState("");
  const [bio, setBio] = useState("");
  const [website, setWebsite] = useState("");
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [appName, setAppName] = useState("");
  const [packageId, setPackageId] = useState("");
  const [appPlatform, setAppPlatform] = useState("Google Play");
  const [developerName, setDeveloperName] = useState("");

  async function runAnalysis() {
    setLoading(true); setError(""); setResult(null);
    await new Promise(r => setTimeout(r, 1400)); // brief analysis UX delay
    try {
      let r: AnalysisResult;
      if (activeTab === "name") r = analyzeNameLogic(brandName);
      else if (activeTab === "social") r = analyzeSocialLogic(platform, username, dispName, bio, website);
      else if (activeTab === "website") r = analyzeWebsiteLogic(websiteUrl);
      else r = analyzeAppLogic(appName, packageId, appPlatform, developerName);
      setResult(r);
    } catch (e) {
      setError("Analysis failed — please check your inputs and try again.");
    } finally {
      setLoading(false);
    }
  }

  async function createCase() {
    if (!result) return;
    setCreatingCase(true);
    try {
      /* We need a brand_id. Grab the first brand from the backend. */
      const brands = await api.brands();
      if (!brands.length) throw new Error("No monitored brands found. Seed the demo data first.");
      const brand = brands[0];

      /* Build a synthetic candidate record on the fly via the demo flow
         (the backend doesn't expose a raw "create candidate" endpoint,
         so we create the case referencing the first existing candidate
         whose type matches, then set a descriptive title.) */
      const candidatesPage = await api.candidates({ page_size: 100 });
      const matchType = result.entity_type === "SOCIAL_PROFILE" ? "SOCIAL_PROFILE" : "MOBILE_APP";
      const candidate =
        candidatesPage.items.find((c: Candidate) => c.candidate_type === matchType) ??
        candidatesPage.items[0];

      if (!candidate) throw new Error("No candidates available — seed the demo data first.");

      const caseRecord = await api.createCase({
        candidate_id: candidate.id,
        brand_id: brand.id,
        title: `Analyze: ${result.entity_label} — ${result.risk_level} risk`,
        description:
          `Ad-hoc analysis result.\n` +
          `Entity type: ${result.entity_type}\n` +
          `Risk score: ${result.risk_score}/100 (${result.risk_level})\n` +
          `Signals detected: ${result.signals.length}\n` +
          `Analysis: ${result.explanation}`,
        priority: result.risk_level,
        created_by: typeof window !== "undefined" ? (localStorage.getItem("brandshield_name") ?? "Analyst") : "Analyst",
      });

      notify(`Investigation case created: ${caseRecord.id.slice(0, 8).toUpperCase()}`);
      router.push("/cases");
    } catch (e) {
      notify(e instanceof ApiError ? e.message : String(e instanceof Error ? e.message : "Unable to create case."), "error");
    } finally {
      setCreatingCase(false);
    }
  }

  const canRun =
    !loading && (
      (activeTab === "name" && brandName.trim().length > 0) ||
      (activeTab === "social" && (username.trim() || dispName.trim())) ||
      (activeTab === "website" && websiteUrl.trim().length > 0) ||
      (activeTab === "app" && appName.trim().length > 0)
    );

  const TABS = [
    { id: "name", icon: "◈", label: "Brand Name" },
    { id: "social", icon: "◎", label: "Social Profile" },
    { id: "website", icon: "◐", label: "Website / URL" },
    { id: "app", icon: "▣", label: "Mobile App" },
  ] as const;

  return (
    <>
      <PageHeading
        eyebrow="THREAT ANALYSIS / DETERMINISTIC ENGINE"
        title="Analyze threat"
        description="Submit a brand name, social profile, website, or mobile app for immediate risk assessment."
        action={<span className="synth-badge">SYNTHETIC ANALYSIS · NO LIVE LOOKUP</span>}
      />

      <div className="analyze-shell">
        {/* ── Tab selector ─────────────────── */}
        <div className="analyze-tab-row">
          {TABS.map(t => (
            <button
              key={t.id}
              className={`atab ${activeTab === t.id ? "atab-active" : ""}`}
              onClick={() => { setActiveTab(t.id); setResult(null); setError(""); }}
              type="button"
            >
              <span className="atab-icon">{t.icon}</span>
              <span>{t.label}</span>
            </button>
          ))}
        </div>

        <div className="analyze-body">
          {/* ── Input panel ──────────────────── */}
          <div className="analyze-input-col">
            {activeTab === "name" && (
              <Panel title="Brand / company name" subtitle="Evaluate a name for impersonation risk">
                <div className="afield">
                  <label htmlFor="a-brand">Brand or company name</label>
                  <input id="a-brand" placeholder="e.g. NovaPay, SecureBank, TrustWallet" value={brandName} onChange={e => setBrandName(e.target.value)} onKeyDown={e => e.key === "Enter" && canRun && runAnalysis()} />
                  <small>The engine checks keyword patterns, brand similarity, and character substitution.</small>
                </div>
                <button className="button-primary analyze-run-btn" onClick={runAnalysis} disabled={!canRun}>
                  {loading ? <><span className="btn-spinner" />Analyzing…</> : <>Analyze Brand Name →</>}
                </button>
              </Panel>
            )}
            {activeTab === "social" && (
              <Panel title="Social profile" subtitle="Assess a social media account for impersonation">
                <div className="afield-row">
                  <div className="afield">
                    <label htmlFor="a-platform">Platform</label>
                    <select id="a-platform" value={platform} onChange={e => setPlatform(e.target.value)}>
                      <option>Instagram</option><option>Facebook</option><option>Twitter / X</option>
                      <option>LinkedIn</option><option>TikTok</option><option>YouTube</option>
                    </select>
                  </div>
                  <div className="afield">
                    <label htmlFor="a-username">Username</label>
                    <input id="a-username" placeholder="username (no @)" value={username} onChange={e => setUsername(e.target.value)} />
                  </div>
                </div>
                <div className="afield">
                  <label htmlFor="a-dispname">Display name <span className="opt-tag">optional</span></label>
                  <input id="a-dispname" placeholder="Profile display name" value={dispName} onChange={e => setDispName(e.target.value)} />
                </div>
                <div className="afield">
                  <label htmlFor="a-bio">Bio / description <span className="opt-tag">optional</span></label>
                  <textarea id="a-bio" rows={3} placeholder="Paste profile bio or description" value={bio} onChange={e => setBio(e.target.value)} />
                </div>
                <div className="afield">
                  <label htmlFor="a-web">External link <span className="opt-tag">optional</span></label>
                  <input id="a-web" placeholder="https://external-link.com" value={website} onChange={e => setWebsite(e.target.value)} />
                </div>
                <button className="button-primary analyze-run-btn" onClick={runAnalysis} disabled={!canRun}>
                  {loading ? <><span className="btn-spinner" />Analyzing…</> : <>Analyze Social Profile →</>}
                </button>
              </Panel>
            )}
            {activeTab === "website" && (
              <Panel title="Website / URL" subtitle="Pattern-based domain and URL risk analysis">
                <div className="afield">
                  <label htmlFor="a-url">Website URL or domain</label>
                  <input id="a-url" placeholder="https://example.com or example.com" value={websiteUrl} onChange={e => setWebsiteUrl(e.target.value)} onKeyDown={e => e.key === "Enter" && canRun && runAnalysis()} />
                  <small>The engine inspects TLD, domain structure, keywords, and HTTPS status. No live request is made to the target.</small>
                </div>
                <div className="anotice"><span className="anotice-icon">ℹ</span><span><strong>Safe analysis:</strong> this is a local pattern check only — no HTTP requests are sent to the supplied URL.</span></div>
                <button className="button-primary analyze-run-btn" onClick={runAnalysis} disabled={!canRun}>
                  {loading ? <><span className="btn-spinner" />Analyzing…</> : <>Analyze URL →</>}
                </button>
              </Panel>
            )}
            {activeTab === "app" && (
              <Panel title="Mobile application" subtitle="Assess a mobile app for impersonation and package anomalies">
                <div className="afield-row">
                  <div className="afield">
                    <label htmlFor="a-appname">App name</label>
                    <input id="a-appname" placeholder="e.g. NovaPay Official" value={appName} onChange={e => setAppName(e.target.value)} />
                  </div>
                  <div className="afield">
                    <label htmlFor="a-store">App store</label>
                    <select id="a-store" value={appPlatform} onChange={e => setAppPlatform(e.target.value)}>
                      <option>Google Play</option><option>Apple App Store</option>
                      <option>Samsung Galaxy Store</option><option>Amazon Appstore</option>
                    </select>
                  </div>
                </div>
                <div className="afield">
                  <label htmlFor="a-pkg">Package ID <span className="opt-tag">optional</span></label>
                  <input id="a-pkg" placeholder="com.company.appname" value={packageId} onChange={e => setPackageId(e.target.value)} />
                </div>
                <div className="afield">
                  <label htmlFor="a-dev">Developer name <span className="opt-tag">optional</span></label>
                  <input id="a-dev" placeholder="Developer or company name" value={developerName} onChange={e => setDeveloperName(e.target.value)} />
                </div>
                <div className="anotice"><span className="anotice-icon">ℹ</span><span><strong>Demo mode:</strong> analysis uses deterministic rules — no live app store connection is made.</span></div>
                <button className="button-primary analyze-run-btn" onClick={runAnalysis} disabled={!canRun}>
                  {loading ? <><span className="btn-spinner" />Analyzing…</> : <>Analyze Mobile App →</>}
                </button>
              </Panel>
            )}
          </div>

          {/* ── Results panel ─────────────────── */}
          <div className="analyze-result-col">
            {loading && (
              <div className="analyze-loading">
                <div className="analyze-loading-ring" />
                <p>Running deterministic analysis…</p>
                <small>Evaluating patterns, signals, and known brand indicators</small>
              </div>
            )}

            {error && !loading && (
              <div className="analyze-err">
                <span className="analyze-err-icon">!</span>
                <div><strong>Analysis failed</strong><p>{error}</p></div>
              </div>
            )}

            {result && !loading && (
              <div className="ar-stack">
                {/* Score card */}
                <div className={`ar-score-card risk-border-${result.risk_level.toLowerCase()}`}>
                  <div className="ar-score-left">
                    <div className={`ar-ring ar-ring-${result.risk_level.toLowerCase()}`}>
                      <span className="ar-ring-score">{result.risk_score}</span>
                      <span className="ar-ring-denom">/100</span>
                    </div>
                    <div>
                      <RiskBadge level={result.risk_level} />
                      <div className="ar-entity-label">{result.entity_label}</div>
                      <div className="ar-entity-type">{result.entity_type.replace(/_/g, " ")}</div>
                    </div>
                  </div>
                  <div className="ar-action-box">
                    <div className="ar-action-label">RECOMMENDED ACTION</div>
                    <p>{result.recommended_action}</p>
                  </div>
                </div>

                {/* Summary */}
                <div className="ar-section">
                  <div className="ar-section-title">Analysis summary</div>
                  <p className="ar-summary">{result.explanation}</p>
                </div>

                {/* Signals */}
                {result.signals.length > 0 && (
                  <div className="ar-section">
                    <div className="ar-section-title">Risk signals detected <span className="ar-count">{result.signals.length}</span></div>
                    <div className="ar-signals">
                      {result.signals.map((sig, i) => (
                        <div className="ar-signal" key={i}>
                          <div className="ar-signal-top">
                            <span className="ar-signal-name">{sig.name}</span>
                            <span className="ar-signal-pts">+{sig.score} pts</span>
                          </div>
                          <p className="ar-signal-desc">{sig.explanation}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* No signals */}
                {result.signals.length === 0 && (
                  <div className="ar-section">
                    <div className="ar-section-title">Risk signals</div>
                    <p className="ar-summary">No risk signals detected. The entity appears low-risk based on current pattern rules.</p>
                  </div>
                )}

                {/* Meta */}
                <div className="ar-meta">
                  <span>Engine: Deterministic Multi-Signal</span>
                  <span>Confidence: Rule-based</span>
                  <span>Generated: {new Date(result.generated_at).toLocaleString()}</span>
                </div>

                {/* Actions */}
                <div className="ar-actions">
                  <button
                    className="button-primary"
                    onClick={createCase}
                    disabled={creatingCase}
                  >
                    {creatingCase ? <><span className="btn-spinner" />Creating case…</> : <>＋ Create Investigation Case</>}
                  </button>
                  <button
                    className="button-secondary"
                    onClick={() => { setResult(null); setError(""); }}
                  >
                    Clear result
                  </button>
                </div>
              </div>
            )}

            {!result && !loading && !error && (
              <div className="analyze-empty">
                <div className="analyze-empty-icon">◈</div>
                <h3>No analysis yet</h3>
                <p>Fill in the form on the left and click <strong>Analyze</strong> to run a deterministic risk assessment.</p>
                <div className="analyze-empty-chips">
                  <span>Brand names</span><span>Social profiles</span><span>Websites</span><span>Mobile apps</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
