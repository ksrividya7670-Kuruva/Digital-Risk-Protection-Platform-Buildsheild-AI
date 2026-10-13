/**
 * Static API — replaces network calls for GitHub Pages build.
 * Serves the embedded synthetic dataset from demo-data.ts.
 * All mutations (createCase, updateCase) persist to localStorage.
 */

import {
  DEMO_CANDIDATES,
  DEMO_BRAND,
  DEMO_BRAND_SUMMARY,
  DEMO_ANALYTICS,
  DEMO_TRENDS,
  DEMO_CASES_INITIAL,
} from "./demo-data";

import type {
  Candidate, CandidateDetail, Brand, BrandSummary,
  CaseRecord, CaseStatus, Analytics, TrendPoint,
  Investigation, AnalystAnswer, PageResult, RiskLevel,
} from "./api";

const CASES_KEY = "brandshield_cases";

function loadCases(): CaseRecord[] {
  if (typeof window === "undefined") return [...DEMO_CASES_INITIAL];
  try {
    const stored = localStorage.getItem(CASES_KEY);
    return stored ? (JSON.parse(stored) as CaseRecord[]) : [...DEMO_CASES_INITIAL];
  } catch { return [...DEMO_CASES_INITIAL]; }
}

function saveCases(cases: CaseRecord[]) {
  if (typeof window !== "undefined") localStorage.setItem(CASES_KEY, JSON.stringify(cases));
}

function delay(ms = 300): Promise<void> {
  return new Promise(r => setTimeout(r, ms));
}

/* ── helpers ─────────────────────────────────────────────────── */
function toCandidate(d: CandidateDetail): Candidate {
  return {
    id: d.id, brand_id: d.brand_id, candidate_type: d.candidate_type,
    platform: d.platform, name: d.name, username: d.username,
    risk_score: d.risk_score, risk_level: d.risk_level, confidence: d.confidence,
    status: d.status, data_source: d.data_source, discovered_at: d.discovered_at,
  };
}

function buildInvestigation(d: CandidateDetail): Investigation {
  const topSignals = [...d.signals]
    .sort((a, b) => b.weighted_score - a.weighted_score)
    .slice(0, 4)
    .map(s => `${s.signal_name.replace(/_/g, " ")}: ${s.weighted_score.toFixed(1)}/${s.weight} pts`);

  const evSummary = d.evidence.length
    ? d.evidence.map(e => `${e.title} — ${e.description ?? ""}`)
    : ["No stored evidence records are attached to this candidate."];

  const actions: string[] = [];
  if (d.risk_level === "CRITICAL" || d.risk_level === "HIGH") {
    actions.push("Preserve all evidence before taking action.", "Verify official brand ownership.", "Consider platform takedown if impersonation is confirmed.");
  } else {
    actions.push("Monitor for further risk escalation.", "No immediate action required at this time.");
  }
  actions.push("Update case status as investigation progresses.");

  return {
    candidate_id: d.id,
    risk_score: d.risk_score ?? 0,
    risk_level: d.risk_level ?? "LOW",
    summary: d.detection_summary ?? `This ${d.candidate_type.replace("_", " ").toLowerCase()} on ${d.platform} scored ${d.risk_score}/100 (${d.risk_level}) against brand '${d.brand_name}'.`,
    risk_explanation: `The deterministic engine assigned a score of ${d.risk_score}/100 (${d.risk_level}) based on ${d.signals.length} weighted signals. Key factors: ${topSignals.slice(0, 2).join("; ")}.`,
    key_findings: topSignals.length ? topSignals : ["No significant signals detected."],
    evidence_summary: evSummary,
    recommended_actions: actions,
    confidence_note: `Engine confidence: ${Math.round((d.confidence ?? 0.5) * 100)}%. ${d.evidence.length} evidence record(s) attached.`,
    ai_verdict: d.risk_level === "CRITICAL" ? "AI_VERDICT_LIKELY_FAKE" : d.risk_level === "HIGH" ? "AI_VERDICT_SUSPICIOUS" : "AI_VERDICT_LIKELY_LEGITIMATE",
    ai_verdict_reasoning: `Based on ${d.signals.length} signals and ${d.evidence.length} evidence records.`,
    threat_confidence: d.risk_score ?? 0,
    generated_by: "template",
    generated_at: new Date().toISOString(),
  };
}

/* ── Static API surface ─────────────────────────────────────── */
export const staticApi = {
  candidates: async (filters: Record<string, string | number | undefined> = {}): Promise<PageResult<Candidate>> => {
    await delay(250);
    let items = DEMO_CANDIDATES.map(toCandidate);
    if (filters.risk_level) items = items.filter(c => c.risk_level === filters.risk_level);
    if (filters.candidate_type) items = items.filter(c => c.candidate_type === filters.candidate_type);
    if (filters.platform) items = items.filter(c => c.platform === filters.platform);
    if (filters.sort === "risk_score_desc") items.sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0));
    const page = Number(filters.page ?? 1);
    const pageSize = Number(filters.page_size ?? 100);
    const start = (page - 1) * pageSize;
    return { items: items.slice(start, start + pageSize), page, page_size: pageSize, total: items.length };
  },

  candidate: async (id: string): Promise<CandidateDetail> => {
    await delay(200);
    const found = DEMO_CANDIDATES.find(c => c.id === id);
    if (!found) throw new Error(`Candidate ${id} not found`);
    return found;
  },

  brands: async (): Promise<Brand[]> => {
    await delay(200);
    return [DEMO_BRAND];
  },

  brandSummary: async (_id: string): Promise<BrandSummary> => {
    await delay(150);
    return DEMO_BRAND_SUMMARY;
  },

  cases: async (filters: Record<string, string | number | undefined> = {}): Promise<PageResult<CaseRecord>> => {
    await delay(250);
    let items = loadCases();
    if (filters.status) items = items.filter(c => c.status === filters.status);
    const page = Number(filters.page ?? 1);
    const pageSize = Number(filters.page_size ?? 100);
    return { items, page, page_size: pageSize, total: items.length };
  },

  case: async (id: string): Promise<CaseRecord> => {
    await delay(200);
    const found = loadCases().find(c => c.id === id);
    if (!found) throw new Error(`Case ${id} not found`);
    return found;
  },

  createCase: async (data: { candidate_id: string; brand_id: string; title: string; description?: string; priority: RiskLevel; created_by: string; }): Promise<CaseRecord> => {
    await delay(400);
    const now = new Date().toISOString();
    const newCase: CaseRecord = {
      id: `case-${Date.now()}`, title: data.title, status: "OPEN",
      priority: data.priority, assigned_to: data.created_by,
      candidate_id: data.candidate_id, brand_id: data.brand_id,
      created_at: now, updated_at: now,
      description: data.description ?? null, created_by: data.created_by,
      resolved_at: null, resolution_notes: null, notes: [],
    };
    const cases = loadCases();
    cases.unshift(newCase);
    saveCases(cases);
    return newCase;
  },

  updateCase: async (id: string, status: CaseStatus): Promise<CaseRecord> => {
    await delay(300);
    const cases = loadCases();
    const idx = cases.findIndex(c => c.id === id);
    if (idx === -1) throw new Error(`Case ${id} not found`);
    cases[idx] = { ...cases[idx], status, updated_at: new Date().toISOString() };
    saveCases(cases);
    return cases[idx];
  },

  analytics: async (): Promise<Analytics> => {
    await delay(200);
    // Merge static data with live case count
    const cases = loadCases();
    const openCases = cases.filter(c => c.status === "OPEN" || c.status === "INVESTIGATING").length;
    return { ...DEMO_ANALYTICS, open_cases: openCases };
  },

  trends: async (): Promise<TrendPoint[]> => {
    await delay(150);
    return DEMO_TRENDS;
  },

  analyze: async (id: string): Promise<Investigation> => {
    await delay(600);
    const candidate = DEMO_CANDIDATES.find(c => c.id === id);
    if (!candidate) throw new Error(`Candidate ${id} not found`);
    return buildInvestigation(candidate);
  },

  ask: async (id: string, question: string): Promise<AnalystAnswer> => {
    await delay(500);
    const candidate = DEMO_CANDIDATES.find(c => c.id === id);
    if (!candidate) throw new Error(`Candidate ${id} not found`);
    const q = question.toLowerCase();
    let answer = "";
    if (q.includes("why") || q.includes("flagged") || q.includes("reason")) {
      const top = [...candidate.signals].sort((a, b) => b.weighted_score - a.weighted_score)[0];
      answer = `This ${candidate.candidate_type.replace("_", " ").toLowerCase()} scored ${candidate.risk_score}/100 (${candidate.risk_level}). The top contributing signal is "${top?.signal_name.replace(/_/g, " ")}" (${top?.weighted_score.toFixed(1)} pts). ${candidate.detection_summary ?? ""}`;
    } else if (q.includes("evidence") || q.includes("proof")) {
      answer = candidate.evidence.length
        ? `${candidate.evidence.length} evidence record(s): ${candidate.evidence.map(e => e.title).join("; ")}.`
        : "No stored evidence records are attached. Review the signal breakdown for contributing factors.";
    } else if (q.includes("signal") || q.includes("score")) {
      const sorted = [...candidate.signals].sort((a, b) => b.weighted_score - a.weighted_score).slice(0, 3);
      answer = `Top signals: ${sorted.map(s => `${s.signal_name.replace(/_/g, " ")} (${s.weighted_score.toFixed(1)} pts)`).join(", ")}.`;
    } else if (q.includes("action") || q.includes("next") || q.includes("recommend")) {
      answer = candidate.risk_level === "CRITICAL" || candidate.risk_level === "HIGH"
        ? "Immediate action recommended: preserve evidence, verify brand ownership, and consider platform takedown request."
        : "Low immediate priority. Continue monitoring and update the case status as new information emerges.";
    } else {
      answer = `${candidate.name ?? candidate.username ?? "This entity"} on ${candidate.platform} scored ${candidate.risk_score}/100 (${candidate.risk_level}) against brand '${candidate.brand_name}'. Refer to the signal breakdown and evidence records for full details.`;
    }
    return { candidate_id: id, question, answer, generated_by: "template", generated_at: new Date().toISOString() };
  },

  demoStatus: async () => ({ seeded: true, total_candidates: 20 }),
  seedDemo: async () => ({ message: "Demo dataset already embedded in this static build." }),
};
