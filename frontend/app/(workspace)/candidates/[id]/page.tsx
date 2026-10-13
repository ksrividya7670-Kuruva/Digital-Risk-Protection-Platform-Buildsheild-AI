"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, ApiError, type AnalystAnswer, type CandidateDetail, type CaseRecord, type CaseStatus, type Investigation } from "@/lib/api";
import { formatDate, notify, safeWebUrl } from "@/lib/ui";
import { ErrorState, LoadingState, PageHeading, Panel, RiskBadge, SignalBar } from "@/components/ui";

const SIGNAL_LABELS: Record<string, string> = {
  identity_similarity: "Identity similarity",
  visual_similarity: "Visual / logo similarity",
  content_similarity: "Content / bio similarity",
  link_risk: "Link / contact risk",
  account_anomaly: "Account / app anomaly",
  evidence_score: "Evidence / reputation",
  activity_anomaly: "Activity anomaly",
};

const CASE_STATUSES: CaseStatus[] = ["OPEN", "INVESTIGATING", "ESCALATED", "RESOLVED", "FALSE_POSITIVE"];

export default function CandidateInvestigationPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [candidate, setCandidate] = useState<CandidateDetail | null>(null);
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [investigation, setInvestigation] = useState<Investigation | null>(null);
  const [answer, setAnswer] = useState<AnalystAnswer | null>(null);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [detail, casePage] = await Promise.all([
        api.candidate(id),
        api.cases({ page: 1, page_size: 100 }),
      ]);
      setCandidate({ ...detail, website_url: safeWebUrl(detail.website_url) });
      setCases(casePage.items.filter((record: CaseRecord) => record.candidate_id === id));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to load candidate investigation.");
    } finally { setLoading(false); }
  }, [id]);
  useEffect(() => { void load(); }, [load]);

  async function runAnalysis() {
    setAnalyzing(true);
    try {
      const result = await api.analyze(id);
      setInvestigation(result);
      notify(result.generated_by === "ai" ? "AI investigation generated." : "Evidence-based fallback generated.");
    } catch (caught) {
      notify(caught instanceof ApiError ? caught.message : "Investigation analysis failed.", "error");
    } finally { setAnalyzing(false); }
  }

  async function askAnalyst(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (question.trim().length < 3) return;
    setAsking(true);
    setAnswer(null);
    try {
      setAnswer(await api.ask(id, question.trim()));
    } catch (caught) {
      notify(caught instanceof ApiError ? caught.message : "Could not submit analyst question.", "error");
    } finally { setAsking(false); }
  }

  async function createCase() {
    if (!candidate) return;
    if (!window.confirm("Create a new investigation case for this candidate?")) return;
    try {
      const created = await api.createCase({
        candidate_id: candidate.id,
        brand_id: candidate.brand_id,
        title: `Review: ${candidate.name || candidate.username || candidate.platform} risk assessment`,
        description: candidate.detection_summary || "Analyst review requested from candidate investigation.",
        priority: candidate.risk_level ?? "MEDIUM",
        created_by: "Security Analyst",
      });
      setCases((current) => [created, ...current]);
      notify("Investigation case created.");
    } catch (caught) {
      notify(caught instanceof ApiError ? caught.message : "Unable to create investigation case.", "error");
    }
  }

  async function setCaseStatus(record: CaseRecord, status: CaseStatus) {
    if (!window.confirm(`Change case to ${status.replaceAll("_", " ")}?`)) return;
    try {
      const updated = await api.updateCase(record.id, status);
      setCases((current) => current.map((item) => item.id === record.id ? { ...item, ...updated } : item));
      notify(`Case status updated to ${status.replaceAll("_", " ")}.`);
    } catch (caught) {
      notify(caught instanceof ApiError ? caught.message : "Unable to update case.", "error");
    }
  }

  if (loading) return <LoadingState label="Loading candidate and evidence…" />;
  if (error || !candidate) return <><PageHeading eyebrow="INVESTIGATION / CANDIDATE" title="Candidate investigation" /><ErrorState message={error || "Candidate not found."} retry={() => void load()} /></>;

  const highScore = Math.max(1, ...candidate.signals.map((signal) => signal.weighted_score));
  const profileUrl = safeWebUrl(candidate.profile_url);
  const riskColor = candidate.risk_level
    ? ({
        CRITICAL: "var(--critical)",
        HIGH: "var(--high)",
        MEDIUM: "var(--medium)",
        LOW: "var(--low)",
      }[candidate.risk_level])
    : "#718493";
  const riskPercent = Math.max(0, Math.min(100, candidate.risk_score ?? 0));
  return (
    <>
      <div className="candidate-back"><Link href="/threats">← Back to threat queue</Link><span>CASE INVESTIGATION / {candidate.id.slice(0, 8).toUpperCase()}</span></div>
      <PageHeading
        eyebrow={`${candidate.brand_name ?? "MONITORED BRAND"} / ${candidate.candidate_type === "SOCIAL_PROFILE" ? "SOCIAL PROFILE" : "MOBILE APP"}`}
        title={candidate.name || candidate.username || candidate.platform}
        description={`${candidate.platform} · ${candidate.username ? `@${candidate.username.replace(/^@/, "")} · ` : ""}${candidate.data_source === "MOCK" ? "Synthetic demo record" : candidate.data_source}`}
        action={<div className="candidate-head-risk"><b>{candidate.risk_score ?? "—"}</b><span>/100</span><RiskBadge level={candidate.risk_level} /></div>}
      />
      <div className="candidate-actions">
        <span className="status-chip">ENTITY STATUS · {candidate.status.replaceAll("_", " ")}</span>
        {profileUrl && <a className="button-secondary" href={profileUrl} target="_blank" rel="noreferrer">Open recorded profile ↗</a>}
        <button className="button-primary" onClick={() => void createCase()}>＋ Create case</button>
      </div>

      <div className="investigation-layout">
        <div className="investigation-main">
          <Panel title="Deterministic risk overview" subtitle="The detection engine is the source of truth; AI does not alter this assessment." className="risk-overview">
            <div className="score-overview">
              <div className={`score-ring ring-${(candidate.risk_level ?? "low").toLowerCase()}`} style={{ background: `conic-gradient(${riskColor} 0 ${riskPercent}%, rgba(139,169,190,.1) ${riskPercent}% 100%)` }}><div><b>{candidate.risk_score ?? "—"}</b><small>RISK SCORE</small></div></div>
              <div className="score-description"><RiskBadge level={candidate.risk_level} /><h3>{candidate.risk_level ? `${candidate.risk_level} risk assessment` : "Not yet assessed"}</h3><p>{candidate.detection_summary || "No deterministic detection summary was recorded for this entity."}</p><div className="confidence-indicator"><span>ENGINE CONFIDENCE</span><b>{candidate.confidence == null ? "—" : `${Math.round(candidate.confidence * 100)}%`}</b><small>Independent of risk score</small></div></div>
            </div>
            <div className="signal-breakdown">
              <div className="signal-breakdown-head"><h3>Signal contribution</h3><span>Weighted points contributed to score</span></div>
              {candidate.signals.length ? candidate.signals.map((signal) => <SignalBar key={signal.signal_name} label={SIGNAL_LABELS[signal.signal_name] ?? signal.signal_name.replaceAll("_", " ")} value={signal.weighted_score} max={signal.weight} />) : <p className="muted">No signal breakdown has been recorded.</p>}
            </div>
            <div className="contribution-bars" role="img" aria-label="Signal contribution chart">{candidate.signals.map((signal) => <div key={signal.signal_name} title={`${SIGNAL_LABELS[signal.signal_name] ?? signal.signal_name}: ${signal.weighted_score.toFixed(1)} points`}><span style={{ height: `${Math.max(3, (signal.weighted_score / highScore) * 100)}%` }} /><small>{(SIGNAL_LABELS[signal.signal_name] ?? signal.signal_name).split(" ")[0]}</small></div>)}</div>
          </Panel>

          <Panel title="Observed evidence" subtitle={`${candidate.evidence.length} evidence record${candidate.evidence.length === 1 ? "" : "s"} attached by backend`}>
            {candidate.evidence.length === 0 ? <div className="chart-empty">No stored evidence is attached. No evidence has been fabricated for this view.</div> : <div className="evidence-list">{candidate.evidence.map((evidence) => <article className="evidence-card" key={evidence.id}>
              <div className="evidence-card-head"><span className="evidence-type">{evidence.evidence_type.replaceAll("_", " ")}</span><span className={`severity-pill severity-${evidence.severity.toLowerCase()}`}>{evidence.severity}</span>{evidence.is_synthetic && <span className="synthetic-pill">SYNTHETIC DEMO</span>}</div>
              <h3>{evidence.title}</h3>
              <p>{evidence.description || "No evidence description recorded."}</p>
              {evidence.evidence_value && <div className="evidence-value"><span>OBSERVED VALUE</span><code>{evidence.evidence_value}</code></div>}
              <div className="evidence-footer"><span>{evidence.source ? `Source: ${evidence.source}` : "Source not recorded"}</span>{evidence.collected_at && <span>Collected {formatDate(evidence.collected_at)}</span>}{safeWebUrl(evidence.source_url) && <a href={safeWebUrl(evidence.source_url) ?? undefined} target="_blank" rel="noreferrer">Open source ↗</a>}</div>
            </article>)}</div>}
          </Panel>

          <Panel title="AI Investigation" subtitle="Analyst assistant · advisory narrative only" action={investigation && <span className={`generated-badge generated-${investigation.generated_by}`}>{investigation.generated_by === "ai" ? "✦ AI-GENERATED" : "◌ TEMPLATE FALLBACK"}</span>}>
            {!investigation ? <div className="ai-empty"><div className="ai-orbit">✦</div><div><b>Generate an evidence-based investigation summary</b><p>Uses the latest stored assessment and evidence. If live AI is unavailable, a deterministic fallback is clearly identified.</p></div><button className="button-primary" disabled={analyzing || !candidate.risk_score} onClick={() => void runAnalysis()}>{analyzing ? "Analyzing…" : "Run investigation"}</button></div> :
              <div className="ai-result">
                <div className="ai-result-meta"><span className={`generated-badge generated-${investigation.generated_by}`}>{investigation.generated_by === "ai" ? "✦ GENERATED BY AI" : "◌ GENERATED BY EVIDENCE-BASED FALLBACK"}</span><small>{formatDate(investigation.generated_at)}</small><button className="button-quiet" disabled={analyzing} onClick={() => void runAnalysis()}>{analyzing ? "Refreshing…" : "Regenerate"}</button></div>
                <div className="ai-summary"><span className="ai-label">INVESTIGATION SUMMARY</span><p>{investigation.summary}</p></div>
                <div className="ai-two-col"><div><h4>Why flagged</h4><p>{investigation.risk_explanation}</p></div><div><h4>Engine confidence</h4><p>{investigation.confidence_note}</p></div></div>
                <div className="ai-two-col"><div><h4>Top contributing signals</h4><ul>{investigation.key_findings.map((finding, index) => <li key={`${finding}-${index}`}>{finding}</li>)}</ul></div><div><h4>Observed evidence <small>from backend records</small></h4>{investigation.evidence_summary.length ? <ul>{investigation.evidence_summary.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul> : <p>No stored evidence.</p>}</div></div>
                <div className="recommendations"><h4>Analyst recommendations <small>NOT OBSERVED EVIDENCE</small></h4><ul>{investigation.recommended_actions.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul></div>
                <p className="ai-advisory">AI assistance does not modify deterministic risk. Verify supplied observations before taking action.</p>
              </div>}
            <form className="analyst-question" onSubmit={(event) => void askAnalyst(event)}><label htmlFor="analyst-question">Ask the analyst assistant</label><div><input id="analyst-question" minLength={3} maxLength={500} value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="What evidence supports the score?" /><button className="button-secondary" type="submit" disabled={asking || question.trim().length < 3}>{asking ? "Asking…" : "Ask question →"}</button></div>{answer && <div className="answer-card"><span className={`generated-badge generated-${answer.generated_by}`}>{answer.generated_by === "ai" ? "AI" : "TEMPLATE"}</span><p>{answer.answer}</p></div>}</form>
          </Panel>
        </div>

        <aside className="investigation-side">
          <Panel title="Entity profile" subtitle="Metadata from the candidate record">
            <dl className="profile-fields"><dt>Brand</dt><dd>{candidate.brand_name ?? "—"}</dd><dt>Type</dt><dd>{candidate.candidate_type.replaceAll("_", " ")}</dd><dt>Platform</dt><dd>{candidate.platform}</dd><dt>Identity</dt><dd>{candidate.username ? `@${candidate.username.replace(/^@/, "")}` : candidate.name || "—"}</dd><dt>Data source</dt><dd>{candidate.data_source}{candidate.data_source === "MOCK" && <span className="synthetic-pill">SYNTHETIC</span>}</dd><dt>First seen</dt><dd>{formatDate(candidate.discovered_at)}</dd>{candidate.website_url && <><dt>Website</dt><dd><a className="safe-link" href={candidate.website_url} target="_blank" rel="noreferrer">{candidate.website_url}</a></dd></>}{candidate.account_age_days != null && <><dt>Account age</dt><dd>{candidate.account_age_days} days</dd></>}{candidate.follower_count != null && <><dt>Followers</dt><dd>{candidate.follower_count.toLocaleString()}</dd></>}{candidate.developer_name && <><dt>Developer</dt><dd>{candidate.developer_name}</dd></>}{candidate.package_name && <><dt>Package</dt><dd>{candidate.package_name}</dd></>}</dl>
          </Panel>
          <Panel title="Case actions" subtitle="Persisted case lifecycle">
            {cases.length === 0 ? <><p className="case-empty-copy">No case is linked to this candidate yet.</p><button className="button-primary full-width" onClick={() => void createCase()}>＋ Create investigation case</button></> : <div className="linked-cases">{cases.map((record) => <article key={record.id}><div className="linked-case-top"><b>{record.title}</b><span className={`case-status status-${record.status.toLowerCase()}`}>{record.status.replaceAll("_", " ")}</span></div><small>{record.id.slice(0, 8)} · updated {formatDate(record.updated_at)}</small><label>Change case status<select className="status-select" value={record.status} onChange={(event) => void setCaseStatus(record, event.target.value as CaseStatus)}>{CASE_STATUSES.map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}</select></label><Link href="/cases" className="text-link">Open case management →</Link></article>)}</div>}
            {cases.length > 0 && <button className="button-secondary full-width" onClick={() => void createCase()}>＋ Create another case</button>}
          </Panel>
          {candidate.bio_description && <Panel title="Profile description"><p className="bio-copy">{candidate.bio_description}</p></Panel>}
        </aside>
      </div>
    </>
  );
}
