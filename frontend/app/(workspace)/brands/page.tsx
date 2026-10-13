"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError, type Brand, type BrandSummary } from "@/lib/api";
import { ErrorState, LoadingState, PageHeading, Panel, StatCard } from "@/components/ui";

export default function BrandsPage() {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [summaries, setSummaries] = useState<Record<string, BrandSummary>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const rows = await api.brands();
      setBrands(rows);
      const summaryRows = await Promise.all(
        rows.map(async (brand) => [brand.id, await api.brandSummary(brand.id)] as const),
      );
      setSummaries(Object.fromEntries(summaryRows));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to load monitored brands.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);
  const all = Object.values(summaries);

  return (
    <>
      <PageHeading eyebrow="ASSET PROTECTION / BRANDS" title="Brand management" description="Monitored brands and their current digital threat exposure." action={<span className="live-pill"><i /> LIVE INVENTORY</span>} />
      {loading ? <LoadingState label="Loading monitored brands…" /> : error ? <ErrorState message={error} retry={() => void load()} /> : (
        <>
          <div className="stats-grid brand-stat-grid">
            <StatCard label="Monitored brands" value={brands.length} icon="◈" />
            <StatCard label="Monitored entities" value={all.reduce((sum, item) => sum + item.total_candidates, 0)} icon="◎" />
            <StatCard label="Critical threats" value={all.reduce((sum, item) => sum + item.critical_threats, 0)} tone="red" icon="!" />
            <StatCard label="Open cases" value={all.reduce((sum, item) => sum + item.open_cases, 0)} icon="▤" />
          </div>
          <Panel title="Protected brands" subtitle="Inventory and threat posture from the backend">
            {brands.length === 0 ? <div className="queue-empty"><b>No monitored brands</b><p>The backend returned no active brands.</p></div> :
              <div className="brand-grid">{brands.map((brand) => {
                const summary = summaries[brand.id];
                return (
                  <article className="brand-card" key={brand.id}>
                    <div className="brand-card-top"><div className="brand-emblem">{brand.name.slice(0, 1).toUpperCase()}</div><span className={`brand-active ${brand.is_active ? "" : "brand-inactive"}`}><i />{brand.is_active ? "MONITORING" : "PAUSED"}</span></div>
                    <h3>{brand.name}</h3>
                    <p className="brand-domain">{brand.official_domain ?? "No official domain recorded"}{brand.industry ? ` · ${brand.industry}` : ""}</p>
                    <div className="brand-id">ID <code>{brand.id}</code></div>
                    <div className="brand-metrics">
                      <div><b>{summary?.total_candidates ?? "—"}</b><small>ENTITIES</small></div>
                      <div><b className="text-critical">{summary?.critical_threats ?? "—"}</b><small>CRITICAL</small></div>
                      <div><b>{summary?.open_cases ?? "—"}</b><small>OPEN CASES</small></div>
                    </div>
                    <div className="brand-platforms"><span>{summary?.social_candidates ?? 0} social profiles</span><span>{summary?.app_candidates ?? 0} apps</span></div>
                    <div className="brand-card-actions"><Link className="button-secondary" href={`/analytics`}>View analytics</Link><Link className="button-primary" href={`/threats?brand_id=${encodeURIComponent(brand.id)}`}>View threats <span>→</span></Link></div>
                  </article>
                );
              })}</div>}
          </Panel>
        </>
      )}
    </>
  );
}
