"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, ApiError, type Candidate, type RiskLevel, type Signal } from "@/lib/api";
import { displayName, formatDate } from "@/lib/ui";
import { ErrorState, LoadingState, PageHeading, Panel, RiskBadge } from "@/components/ui";

const PAGE_SIZE = 10;

export default function ThreatQueuePage() {
  const [items, setItems] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [brandId, setBrandId] = useState("");
  const [candidateType, setCandidateType] = useState("");
  const [platform, setPlatform] = useState("");
  const [riskLevel, setRiskLevel] = useState("");
  const [minScore, setMinScore] = useState("");
  const [maxScore, setMaxScore] = useState("");
  const [sort, setSort] = useState("risk_score_desc");
  const [page, setPage] = useState(1);
  const [brands, setBrands] = useState<Array<{ id: string; name: string }>>([]);
  const [activeSignals, setActiveSignals] = useState<Record<string, number>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [result, brandList] = await Promise.all([
        api.candidates({
          page: 1,
          page_size: 100,
          brand_id: brandId || undefined,
          candidate_type: candidateType || undefined,
          platform: platform || undefined,
          risk_level: riskLevel || undefined,
          min_score: minScore ? Number(minScore) : undefined,
          max_score: maxScore ? Number(maxScore) : undefined,
          sort,
        }),
        api.brands(),
      ]);
      setItems(result.items);
      setBrands(brandList);
      setPage(1);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to load the candidate queue.");
    } finally {
      setLoading(false);
    }
  }, [brandId, candidateType, platform, riskLevel, minScore, maxScore, sort]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    const queryBrand = new URLSearchParams(window.location.search).get("brand_id");
    if (queryBrand) setBrandId(queryBrand);
  }, []);

  const platforms = useMemo(() => Array.from(new Set(items.map((item) => item.platform))).sort(), [items]);
  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return items.filter((item) =>
      !needle ||
      [item.name, item.username, item.platform, item.id]
        .some((value) => value?.toLowerCase().includes(needle)),
    );
  }, [items, search]);
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const visibleIds = currentItems.map((candidate) => candidate.id).join(",");

  useEffect(() => {
    let current = true;
    Promise.all(visibleIds ? visibleIds.split(",").map(async (candidateId) => {
      try {
        const detail = await api.candidate(candidateId);
        return [candidateId, detail.signals.filter((signal: Signal) => signal.weighted_score > 0).length] as const;
      } catch (caught) {
        if (caught instanceof ApiError && caught.status === 404) {
          throw new Error(`Candidate ${candidateId} was removed while loading its signal breakdown.`);
        }
        throw caught;
      }
    }) : []).then((rows) => {
      if (current) setActiveSignals(Object.fromEntries(rows));
    }).catch((caught: unknown) => {
      if (current) setError(caught instanceof Error ? caught.message : "Unable to load signal breakdowns.");
    });
    return () => { current = false; };
  }, [visibleIds]);

  function resetFilters() {
    setSearch("");
    setBrandId("");
    setCandidateType("");
    setPlatform("");
    setRiskLevel("");
    setMinScore("");
    setMaxScore("");
    setSort("risk_score_desc");
    setPage(1);
  }

  return (
    <>
      <PageHeading eyebrow="MONITORING / CANDIDATES" title="Threat queue" description="Review, filter, and investigate suspicious social profiles and mobile apps." action={<span className="queue-count">{filtered.length} <small>ENTITIES</small></span>} />
      {error ? <ErrorState message={error} retry={() => void load()} /> : (
        <Panel title="Candidate monitoring" subtitle="Filtered directly from the current backend dataset" className="queue-panel">
          <div className="filter-toolbar">
            <label className="search-field"><span>⌕</span><input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="Search name, handle, platform…" /></label>
            <select aria-label="Filter by brand" value={brandId} onChange={(event) => setBrandId(event.target.value)}><option value="">All brands</option>{brands.map((brand) => <option key={brand.id} value={brand.id}>{brand.name}</option>)}</select>
            <select aria-label="Filter by type" value={candidateType} onChange={(event) => setCandidateType(event.target.value)}><option value="">All types</option><option value="SOCIAL_PROFILE">Social profile</option><option value="MOBILE_APP">Mobile app</option></select>
            <select aria-label="Filter by platform" value={platform} onChange={(event) => setPlatform(event.target.value)}><option value="">All platforms</option>{platforms.map((name) => <option key={name} value={name}>{name}</option>)}</select>
            <select aria-label="Filter by risk" value={riskLevel} onChange={(event) => setRiskLevel(event.target.value)}><option value="">All risk levels</option>{(["CRITICAL", "HIGH", "MEDIUM", "LOW"] as RiskLevel[]).map((level) => <option key={level} value={level}>{level}</option>)}</select>
            <div className="range-filter"><input aria-label="Minimum score" type="number" min="0" max="100" placeholder="Min" value={minScore} onChange={(event) => setMinScore(event.target.value)} /><span>–</span><input aria-label="Maximum score" type="number" min="0" max="100" placeholder="Max" value={maxScore} onChange={(event) => setMaxScore(event.target.value)} /></div>
            <select aria-label="Sort candidates" value={sort} onChange={(event) => setSort(event.target.value)}><option value="risk_score_desc">Risk: highest</option><option value="risk_score_asc">Risk: lowest</option><option value="newest">First seen: newest</option><option value="oldest">First seen: oldest</option></select>
            <button className="button-quiet reset-button" onClick={resetFilters}>Reset</button>
          </div>
          {loading ? <LoadingState /> : currentItems.length === 0 ? (
            <div className="queue-empty"><div className="empty-mark">⌕</div><b>No matching candidates</b><p>Try changing or resetting the filters.</p></div>
          ) : (
            <div className="table-scroll"><table className="data-table threat-table"><thead><tr><th>Threat</th><th>Type</th><th>Platform</th><th>Identity</th><th>Risk score</th><th>Risk level</th><th>Detection signals</th><th>Status</th><th>First seen</th><th>Action</th></tr></thead><tbody>
              {currentItems.map((item) => <tr key={item.id} className="clickable-row" onClick={() => { window.location.href = `/candidates/${item.id}`; }}>
                <td><Link href={`/candidates/${item.id}`} className="entity-link"><span className={`candidate-avatar ${item.candidate_type === "MOBILE_APP" ? "candidate-app" : ""}`}>{item.candidate_type === "MOBILE_APP" ? "▣" : "◎"}</span></Link></td>
                <td>{item.candidate_type === "SOCIAL_PROFILE" ? "Social" : "App"}</td>
                <td>{item.platform}</td>
                <td><Link href={`/candidates/${item.id}`} className="entity-link"><b>{displayName(item.name, item.username)}</b><small>{item.username ? `@${item.username.replace(/^@/, "")}` : item.id.slice(0, 8)}</small></Link></td>
                <td><b className={`table-score score-${(item.risk_level ?? "low").toLowerCase()}`}>{item.risk_score ?? "—"}</b></td>
                <td><RiskBadge level={item.risk_level} /></td>
                <td><span className="signal-count">{item.risk_score == null ? "Not assessed" : `${activeSignals[item.id] ?? "—"} active`}</span></td>
                <td><span className="status-text">{item.status.replaceAll("_", " ")}</span></td>
                <td>{formatDate(item.discovered_at)}</td>
                <td><Link className="button-small" href={`/candidates/${item.id}`}>Investigate</Link></td>
              </tr>)}
            </tbody></table></div>
          )}
          <div className="table-footer"><span>Showing {currentItems.length ? (page - 1) * PAGE_SIZE + 1 : 0}–{Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length}</span><div className="pagination"><button disabled={page <= 1} onClick={() => setPage(page - 1)}>← Previous</button><span>{page} / {pageCount}</span><button disabled={page >= pageCount} onClick={() => setPage(page + 1)}>Next →</button></div></div>
        </Panel>
      )}
    </>
  );
}
