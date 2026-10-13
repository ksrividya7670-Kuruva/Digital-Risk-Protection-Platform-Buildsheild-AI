"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError, type Analytics, type Candidate, type Signal, type TrendPoint } from "@/lib/api";
import { ErrorState, LoadingState, PageHeading, Panel, StatCard } from "@/components/ui";

const SIGNAL_LABELS: Record<string, string> = {
  identity_similarity: "Identity similarity",
  visual_similarity: "Visual / logo similarity",
  content_similarity: "Content / bio similarity",
  link_risk: "Link / contact risk",
  account_anomaly: "Account / app anomaly",
  evidence_score: "Evidence / reputation",
  activity_anomaly: "Activity anomaly",
};

export default function AnalyticsPage() {
  const [overview, setOverview] = useState<Analytics | null>(null);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [signalTotals, setSignalTotals] = useState<Record<string, { total: number; max: number }>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [stats, trend, candidatePage] = await Promise.all([
        api.analytics(),
        api.trends(),
        api.candidates({ page: 1, page_size: 100 }),
      ]);
      setOverview(stats);
      setTrends(trend);
      setCandidates(candidatePage.items);
      const candidateDetails = await Promise.all(
        candidatePage.items.slice(0, 30).map((candidate) => api.candidate(candidate.id)),
      );
      const totals: Record<string, { total: number; max: number }> = {};
      candidateDetails.forEach((detail) => {
        detail.signals.forEach((signal: Signal) => {
          const value = totals[signal.signal_name] ?? { total: 0, max: 0 };
          value.total += signal.weighted_score;
          value.max += signal.weight;
          totals[signal.signal_name] = value;
        });
      });
      setSignalTotals(totals);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to load analytics.");
    } finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  if (loading) return <LoadingState label="Computing analytics from backend data…" />;
  return (
    <>
      <PageHeading eyebrow="INTELLIGENCE / ANALYTICS" title="Threat analytics" description="Risk and coverage metrics aggregated from current backend assessments." action={<span className="live-pill"><i /> DATABASE AGGREGATES</span>} />
      {error ? <ErrorState message={error} retry={() => void load()} /> : <>
        <div className="stats-grid analytics-stat-grid">
          <StatCard label="Monitored entities" value={overview?.total_candidates ?? 0} icon="◈" />
          <StatCard label="Social profiles" value={overview?.social_candidates ?? 0} icon="◎" />
          <StatCard label="Mobile applications" value={overview?.app_candidates ?? 0} icon="▣" />
          <StatCard label="Average risk score" value={overview?.avg_score.toFixed(1) ?? "0.0"} detail={`Highest ${overview?.max_score ?? 0}`} tone="orange" icon="↗" />
        </div>
        <div className="analytics-grid">
          <Panel title="Risk-level distribution" subtitle="Latest assessment per candidate">
            <div className="analytics-risk-list">{([
              ["CRITICAL", overview?.critical ?? 0, "var(--critical)"],
              ["HIGH", overview?.high ?? 0, "var(--high)"],
              ["MEDIUM", overview?.medium ?? 0, "var(--medium)"],
              ["LOW", overview?.low ?? 0, "var(--low)"],
            ] as const).map(([name, count, color]) => <div className="analytics-risk-row" key={name}><span><i style={{ background: color }} />{name}</span><div className="platform-track"><i style={{ width: `${overview?.total_candidates ? (count / overview.total_candidates) * 100 : 0}%`, background: color }} /></div><b>{count}</b></div>)}</div>
          </Panel>
          <Panel title="Social vs. app threats" subtitle="Monitored entities by candidate classification">
            <div className="type-split analytics-type">
              <div className="type-stat"><span className="type-symbol">◎</span><div><b>{overview?.social_candidates ?? 0}</b><small>Social profiles</small></div><span className="type-share">{overview?.total_candidates ? Math.round((overview.social_candidates / overview.total_candidates) * 100) : 0}%</span></div>
              <div className="type-track"><span style={{ width: `${overview?.total_candidates ? (overview.social_candidates / overview.total_candidates) * 100 : 0}%` }} /></div>
              <div className="type-stat"><span className="type-symbol app-symbol">▣</span><div><b>{overview?.app_candidates ?? 0}</b><small>Mobile apps</small></div><span className="type-share">{overview?.total_candidates ? Math.round((overview.app_candidates / overview.total_candidates) * 100) : 0}%</span></div>
              <div className="type-track app-track"><span style={{ width: `${overview?.total_candidates ? (overview.app_candidates / overview.total_candidates) * 100 : 0}%` }} /></div>
            </div>
          </Panel>
          <Panel title="Discovery trend" subtitle="Daily discovered entities · last 30 days" className="analytics-wide">
            {trends.length ? <div className="trend-chart trend-large" role="img" aria-label="Daily discovery trend"><div className="trend-bars">{trends.map((point) => <div className="trend-column" key={point.date} title={`${point.date}: ${point.count}`}><span style={{ height: `${Math.max(5, (point.count / Math.max(1, ...trends.map((item) => item.count))) * 100)}%` }} /><small>{new Date(point.date).getDate()}</small></div>)}</div><div className="chart-axis"><span>{trends[0].date}</span><span>{trends[trends.length - 1].date}</span></div></div> : <div className="chart-empty">No recorded discoveries in the last 30 days. History is not fabricated.</div>}
          </Panel>
          <Panel title="Platform distribution" subtitle="Observed candidate counts">
            {Object.keys(overview?.by_platform ?? {}).length ? <div className="platform-list">{Object.entries(overview!.by_platform).sort((a, b) => b[1] - a[1]).map(([platform, count]) => <div className="platform-row" key={platform}><span>{platform}</span><div className="platform-track"><i style={{ width: `${(count / Math.max(...Object.values(overview!.by_platform))) * 100}%` }} /></div><b>{count}</b></div>)}</div> : <div className="chart-empty">No platform records available.</div>}
          </Panel>
          <Panel title="Detection signal contribution" subtitle={`Aggregate weighted contributions across ${Math.min(candidates.length, 30)} inspected candidates`} className="analytics-wide">
            {Object.keys(signalTotals).length ? <div className="signal-analytics">{Object.entries(signalTotals).map(([name, item]) => <div className="signal-row" key={name}><div className="signal-label"><span>{SIGNAL_LABELS[name] ?? name.replaceAll("_", " ")}</span><b>{item.total.toFixed(1)} <small>/ {item.max}</small></b></div><div className="signal-track"><span style={{ width: `${item.max ? Math.min(100, (item.total / item.max) * 100) : 0}%` }} /></div></div>)}</div> : <div className="chart-empty">Signal data is not available for current candidates.</div>}
          </Panel>
        </div>
      </>}
    </>
  );
}
