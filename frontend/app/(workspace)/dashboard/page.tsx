"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, type Analytics, type Candidate, type CaseRecord, type TrendPoint, ApiError } from "@/lib/api";
import { displayName, formatDate } from "@/lib/ui";
import { EmptyState, ErrorState, LoadingState, PageHeading, Panel, RiskBadge, StatCard } from "@/components/ui";

export default function DashboardPage() {
  const [overview, setOverview] = useState<Analytics | null>(null);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [seedMessage, setSeedMessage] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [stats, trend, threats, casePage] = await Promise.all([
        api.analytics(),
        api.trends(),
        api.candidates({ page_size: 100, sort: "risk_score_desc" }),
        api.cases({ page_size: 5 }),
      ]);
      setOverview(stats);
      setTrends(trend);
      setCandidates(threats.items.slice(0, 6));
      setCases(casePage.items.slice(0, 5));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function seedDemo() {
    setSeeding(true);
    setSeedMessage("");
    try {
      await api.seedDemo();
      setSeedMessage("Synthetic demo dataset is ready.");
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to seed demo data.");
    } finally {
      setSeeding(false);
    }
  }

  if (loading) return <LoadingState label="Loading security overview…" />;
  if (error) {
    return (
      <>
        <PageHeading eyebrow="SECURITY OPERATIONS / OVERVIEW" title="Executive dashboard" description="Live overview of monitored entities and digital risk." />
        <ErrorState message={error} retry={() => void load()} />
      </>
    );
  }

  const hasData = (overview?.total_candidates ?? 0) > 0;
  const riskItems = [
    ["CRITICAL", overview?.critical ?? 0, "var(--critical)"],
    ["HIGH", overview?.high ?? 0, "var(--high)"],
    ["MEDIUM", overview?.medium ?? 0, "var(--medium)"],
    ["LOW", overview?.low ?? 0, "var(--low)"],
  ] as const;
  const trendMax = Math.max(1, ...trends.map((point) => point.count));

  return (
    <>
      <PageHeading
        eyebrow="SECURITY OPERATIONS / OVERVIEW"
        title="Executive dashboard"
        description="Real-time visibility into your monitored digital footprint."
        action={<span className="live-pill"><i /> LIVE DATA</span>}
      />
      {!hasData && (
        <div className="seed-banner">
          <div><b>Demo workspace is waiting for data</b><p>Load the backend&apos;s synthetic dataset to populate the dashboard.</p></div>
          <button className="button-primary" disabled={seeding} onClick={() => void seedDemo()}>{seeding ? "Preparing…" : "Load demo dataset"}</button>
        </div>
      )}
      {seedMessage && <div className="inline-success">{seedMessage}</div>}
      <div className="stats-grid">
        <StatCard label="Monitored entities" value={overview?.total_candidates ?? 0} detail="Across all platforms" icon="◈" />
        <StatCard label="Critical threats" value={overview?.critical ?? 0} detail="Immediate review" tone="red" icon="!" />
        <StatCard label="High risk" value={overview?.high ?? 0} detail="Priority queue" tone="orange" icon="↗" />
        <StatCard label="Medium risk" value={overview?.medium ?? 0} detail="Analyst review" tone="yellow" icon="◉" />
        <StatCard label="Low risk" value={overview?.low ?? 0} detail="Monitoring" tone="green" icon="✓" />
        <StatCard label="Open cases" value={overview?.open_cases ?? 0} detail="Active investigations" icon="▤" />
      </div>

      <div className="dashboard-grid">
        <Panel title="Threat distribution" subtitle="Current deterministic risk assessments" className="distribution-panel">
          {!hasData ? <EmptyState title="No assessments yet" detail="Load the demo dataset or connect candidate data to see risk distribution." /> :
            <div className="distribution-content">
              <div className="donut-wrap">
                <div
                  className="donut-chart"
                  style={{
                    background: `conic-gradient(var(--critical) 0 ${(overview!.critical / Math.max(1, overview!.critical + overview!.high + overview!.medium + overview!.low)) * 100}%, var(--high) 0 ${(overview!.critical + overview!.high) / Math.max(1, overview!.critical + overview!.high + overview!.medium + overview!.low) * 100}%, var(--medium) 0 ${(overview!.critical + overview!.high + overview!.medium) / Math.max(1, overview!.critical + overview!.high + overview!.medium + overview!.low) * 100}%, var(--low) 0 100%)`,
                  }}
                ><span><b>{overview?.total_candidates ?? 0}</b><small>ENTITIES</small></span></div>
              </div>
              <div className="distribution-legend">
                {riskItems.map(([level, count, color]) => (
                  <div className="legend-item" key={level}><span><i style={{ background: color }} />{level}</span><b>{count}</b></div>
                ))}
              </div>
            </div>}
        </Panel>

        <Panel title="Threat discovery trend" subtitle="Daily entities detected · last 30 days" action={<span className="subtle-tag">30 DAYS</span>}>
          {trends.length === 0 ? <div className="chart-empty">No discovery history in the selected period.</div> :
            <div className="trend-chart" role="img" aria-label={`${trends.length} daily threat discovery data points`}>
              <div className="trend-bars">
                {trends.map((point) => <div className="trend-column" key={point.date} title={`${point.date}: ${point.count}`}><span style={{ height: `${Math.max(5, (point.count / trendMax) * 100)}%` }} /><small>{new Date(point.date).getDate()}</small></div>)}
              </div>
              <div className="chart-axis"><span>{trends[0]?.date}</span><span>{trends[trends.length - 1]?.date}</span></div>
            </div>}
        </Panel>

        <Panel title="Social vs. app monitoring" subtitle="Monitored candidate type breakdown">
          <div className="type-split">
            <div className="type-stat"><span className="type-symbol">◎</span><div><b>{overview?.social_candidates ?? 0}</b><small>Social profiles</small></div><span className="type-share">{overview?.total_candidates ? Math.round((overview.social_candidates / overview.total_candidates) * 100) : 0}%</span></div>
            <div className="type-track"><span style={{ width: `${overview?.total_candidates ? (overview.social_candidates / overview.total_candidates) * 100 : 0}%` }} /></div>
            <div className="type-stat"><span className="type-symbol app-symbol">▣</span><div><b>{overview?.app_candidates ?? 0}</b><small>Mobile apps</small></div><span className="type-share">{overview?.total_candidates ? Math.round((overview.app_candidates / overview.total_candidates) * 100) : 0}%</span></div>
            <div className="type-track app-track"><span style={{ width: `${overview?.total_candidates ? (overview.app_candidates / overview.total_candidates) * 100 : 0}%` }} /></div>
          </div>
        </Panel>

        <Panel title="Platform exposure" subtitle="Entities by observed platform">
          {Object.keys(overview?.by_platform ?? {}).length === 0 ? <div className="chart-empty">No platform records available.</div> :
            <div className="platform-list">{Object.entries(overview!.by_platform).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([platform, count]) => <div className="platform-row" key={platform}><span>{platform}</span><div className="platform-track"><i style={{ width: `${(count / Math.max(...Object.values(overview!.by_platform))) * 100}%` }} /></div><b>{count}</b></div>)}</div>}
        </Panel>

        <Panel title="Priority threat queue" subtitle="Highest risk candidates from backend" className="wide-panel" action={<Link className="text-link" href="/threats">View queue →</Link>}>
          {candidates.length === 0 ? <EmptyState title="No threats to review" detail="The candidate queue is empty." /> :
            <div className="table-scroll"><table className="data-table"><thead><tr><th>Candidate</th><th>Type / platform</th><th>Risk</th><th>Status</th><th>First seen</th><th /></tr></thead><tbody>{candidates.map((candidate) => <tr key={candidate.id}><td><Link href={`/candidates/${candidate.id}`} className="entity-link"><b>{displayName(candidate.name, candidate.username)}</b><small>{candidate.id.slice(0, 8)} · {candidate.data_source === "MOCK" ? "Synthetic" : "Observed"}</small></Link></td><td><span className="cell-main">{candidate.candidate_type === "SOCIAL_PROFILE" ? "Social profile" : "Mobile app"}</span><small className="cell-sub">{candidate.platform}</small></td><td><RiskBadge level={candidate.risk_level} /><b className="score-inline">{candidate.risk_score ?? "—"}</b></td><td><span className="status-text">{candidate.status.replaceAll("_", " ")}</span></td><td>{formatDate(candidate.discovered_at)}</td><td><Link className="row-arrow" href={`/candidates/${candidate.id}`}>→</Link></td></tr>)}</tbody></table></div>}
        </Panel>

        <Panel title="Recent cases" subtitle="Latest active response workflows" action={<Link className="text-link" href="/cases">All cases →</Link>}>
          {cases.length === 0 ? <div className="chart-empty">No investigation cases have been opened.</div> :
            <div className="recent-cases">{cases.map((record) => <Link href="/cases" className="recent-case" key={record.id}><span className="case-icon">▤</span><span><b>{record.title}</b><small>{record.id.slice(0, 8)} · updated {formatDate(record.updated_at)}</small></span><span className={`case-status status-${record.status.toLowerCase()}`}>{record.status.replaceAll("_", " ")}</span></Link>)}</div>}
        </Panel>
      </div>
    </>
  );
}
