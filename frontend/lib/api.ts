// Use env var when set (e.g. for LAN/production access), otherwise fall back to
// relative URLs so the Next.js rewrite proxy handles dev traffic correctly.
const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/$/, "");

export type RiskLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
export type CandidateType = "SOCIAL_PROFILE" | "MOBILE_APP";
export type CaseStatus =
  | "OPEN"
  | "INVESTIGATING"
  | "ESCALATED"
  | "RESOLVED"
  | "FALSE_POSITIVE";

export interface PageResult<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface Candidate {
  id: string;
  brand_id: string;
  candidate_type: CandidateType;
  platform: string;
  name: string | null;
  username: string | null;
  risk_score: number | null;
  risk_level: RiskLevel | null;
  confidence: number | null;
  status: string;
  data_source: string;
  discovered_at: string | null;
}

export interface Signal {
  signal_name: string;
  raw_score: number;
  weight: number;
  weighted_score: number;
  reason: string;
}

export interface Evidence {
  id: string;
  evidence_type: string;
  severity: string;
  title: string;
  description: string | null;
  evidence_value: string | null;
  similarity_score: number | null;
  source: string | null;
  source_url: string | null;
  is_synthetic: boolean;
  collected_at: string | null;
}

export interface CandidateDetail extends Candidate {
  brand_name: string | null;
  display_name: string | null;
  profile_url: string | null;
  bio_description: string | null;
  website_url: string | null;
  contact_email: string | null;
  icon_url: string | null;
  follower_count: number | null;
  following_count: number | null;
  account_age_days: number | null;
  is_verified: boolean | null;
  package_name: string | null;
  developer_name: string | null;
  developer_email: string | null;
  app_version: string | null;
  install_count: number | null;
  app_rating: string | null;
  detection_summary: string | null;
  ai_explanation: string | null;
  signals: Signal[];
  evidence: Evidence[];
}

export interface Brand {
  id: string;
  name: string;
  official_domain: string | null;
  industry: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BrandSummary {
  brand_id: string;
  brand_name: string;
  total_candidates: number;
  social_candidates: number;
  app_candidates: number;
  critical_threats: number;
  high_threats: number;
  medium_threats: number;
  low_threats: number;
  open_cases: number;
}

export interface CaseRecord {
  id: string;
  title: string;
  status: CaseStatus;
  priority: RiskLevel;
  assigned_to: string | null;
  candidate_id: string;
  brand_id: string;
  created_at: string;
  updated_at: string;
  description?: string | null;
  created_by?: string | null;
  resolved_at?: string | null;
  resolution_notes?: string | null;
  notes?: Array<{ id: string; author: string; content: string; created_at: string }>;
}

export interface Analytics {
  total_candidates: number;
  social_candidates: number;
  app_candidates: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  avg_score: number;
  max_score: number;
  open_cases: number;
  by_platform: Record<string, number>;
  by_type: Record<string, number>;
}

export interface TrendPoint {
  date: string;
  count: number;
}

export interface Investigation {
  candidate_id: string;
  risk_score: number;
  risk_level: RiskLevel;
  summary: string;
  risk_explanation: string;
  key_findings: string[];
  evidence_summary: string[];
  recommended_actions: string[];
  confidence_note: string;
  ai_verdict?: string | null;
  ai_verdict_reasoning?: string | null;
  threat_confidence?: number | null;
  generated_by: "ai" | "template";
  generated_at: string;
}

export interface AnalystAnswer {
  candidate_id: string;
  question: string;
  answer: string;
  generated_by: "ai" | "template";
  generated_at: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      `Cannot connect to the BrandShield API at ${API_BASE}. Start the backend and try again.`,
      0,
    );
  }

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      typeof body?.detail === "string"
        ? body.detail
        : response.status === 404
          ? "The requested record was not found."
          : response.status === 422
            ? "The request was not accepted. Check the supplied filters or data."
            : `The API returned an error (${response.status}).`;
    throw new ApiError(detail, response.status);
  }
  return body as T;
}

export const api = {
  candidates: (filters: Record<string, string | number | undefined> = {}) => {
    const params = new URLSearchParams();
    Object.entries({ page: 1, page_size: 100, ...filters }).forEach(
      ([key, value]) => {
        if (value === undefined || (typeof value === "string" && value === "")) return;
        params.set(key, String(value));
      },
    );
    return request<PageResult<Candidate>>(`/api/v1/candidates/?${params}`);
  },
  candidate: (id: string) =>
    request<CandidateDetail>(`/api/v1/candidates/${encodeURIComponent(id)}`),
  brands: () => request<Brand[]>("/api/v1/brands/"),
  brandSummary: (id: string) =>
    request<BrandSummary>(`/api/v1/brands/${encodeURIComponent(id)}/summary`),
  cases: (filters: Record<string, string | number | undefined> = {}) => {
    const params = new URLSearchParams();
    Object.entries({ page: 1, page_size: 100, ...filters }).forEach(
      ([key, value]) => {
        if (value === undefined || (typeof value === "string" && value === "")) return;
        params.set(key, String(value));
      },
    );
    return request<PageResult<CaseRecord>>(`/api/v1/cases/?${params}`);
  },
  case: (id: string) =>
    request<CaseRecord>(`/api/v1/cases/${encodeURIComponent(id)}`),
  createCase: (data: {
    candidate_id: string;
    brand_id: string;
    title: string;
    description?: string;
    priority: RiskLevel;
    created_by: string;
  }) =>
    request<CaseRecord>("/api/v1/cases/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateCase: (id: string, status: CaseStatus) =>
    request<CaseRecord>(`/api/v1/cases/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  analytics: () => request<Analytics>("/api/v1/analytics/overview"),
  trends: () => request<TrendPoint[]>("/api/v1/analytics/trends"),
  analyze: (id: string) =>
    request<Investigation>(
      `/api/v1/investigation/candidates/${encodeURIComponent(id)}/analyze`,
      { method: "POST" },
    ),
  ask: (id: string, question: string) =>
    request<AnalystAnswer>(
      `/api/v1/investigation/candidates/${encodeURIComponent(id)}/ask`,
      { method: "POST", body: JSON.stringify({ question }) },
    ),
  demoStatus: () => request<{ seeded: boolean; total_candidates?: number }>(
    "/api/v1/demo/status",
  ),
  seedDemo: () =>
    request<{ message: string }>("/api/v1/demo/seed", { method: "POST" }),
};
