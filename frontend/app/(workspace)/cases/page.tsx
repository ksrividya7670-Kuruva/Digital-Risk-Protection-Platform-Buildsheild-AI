"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, ApiError, type Candidate, type CaseRecord, type CaseStatus } from "@/lib/api";
import { displayName, formatDate, notify } from "@/lib/ui";
import { ErrorState, LoadingState, PageHeading, Panel, RiskBadge } from "@/components/ui";

const statuses: CaseStatus[] = ["OPEN", "INVESTIGATING", "ESCALATED", "RESOLVED", "FALSE_POSITIVE"];

export default function CasesPage() {
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState<CaseRecord | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [casePage, candidatePage] = await Promise.all([
        api.cases({ page: 1, page_size: 100, status: filter || undefined }),
        api.candidates({ page: 1, page_size: 100 }),
      ]);
      setCases(casePage.items);
      setCandidates(candidatePage.items);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to load cases.");
    } finally { setLoading(false); }
  }, [filter]);
  useEffect(() => { void load(); }, [load]);

  const candidateById = useMemo(() => new Map(candidates.map((candidate) => [candidate.id, candidate])), [candidates]);

  async function updateStatus(record: CaseRecord, status: CaseStatus) {
    if (status === record.status) return;
    if (!window.confirm(`Change case status from ${record.status.replaceAll("_", " ")} to ${status.replaceAll("_", " ")}?`)) {
      void load();
      return;
    }
    try {
      const updated = await api.updateCase(record.id, status);
      setCases((current) => current.map((item) => item.id === updated.id ? { ...item, ...updated } : item));
      if (selected?.id === updated.id) setSelected({ ...selected, ...updated });
      notify(`Case moved to ${status.replaceAll("_", " ")}.`);
    } catch (caught) {
      notify(caught instanceof ApiError ? caught.message : "Could not update case status.", "error");
      void load();
    }
  }

  return (
    <>
      <PageHeading eyebrow="INCIDENT RESPONSE / CASES" title="Case management" description="Track analyst investigations and persist lifecycle updates to the backend." action={<span className="live-pill"><i /> CASE WORKFLOW</span>} />
      {error ? <ErrorState message={error} retry={() => void load()} /> : (
        <Panel title="Investigation cases" subtitle={`${cases.length} cases returned by the backend`} action={<select className="filter-select" value={filter} onChange={(event) => setFilter(event.target.value)}><option value="">All statuses</option>{statuses.map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}</select>}>
          {loading ? <LoadingState label="Loading investigation cases…" /> : cases.length === 0 ? <div className="queue-empty"><div className="empty-mark">▤</div><b>No cases in this view</b><p>Cases created during candidate investigations will appear here.</p></div> : (
            <div className="table-scroll"><table className="data-table"><thead><tr><th>Case ID</th><th>Candidate</th><th>Risk</th><th>Priority</th><th>Status</th><th>Created at</th><th>Updated at</th><th>View</th></tr></thead><tbody>{cases.map((record) => {
              const candidate = candidateById.get(record.candidate_id);
              return <tr key={record.id}><td><code className="case-id">{record.id.slice(0, 8)}</code><small className="cell-sub">{record.title}</small></td><td>{candidate ? <Link className="table-candidate" href={`/candidates/${candidate.id}`}>{displayName(candidate.name, candidate.username)}</Link> : <span className="muted">Candidate {record.candidate_id.slice(0, 8)}</span>}</td><td><RiskBadge level={candidate?.risk_level} /><b className="score-inline">{candidate?.risk_score ?? "—"}</b></td><td><RiskBadge level={record.priority} /></td><td><select className={`status-select status-${record.status.toLowerCase()}`} aria-label={`Update status for case ${record.id}`} value={record.status} onChange={(event) => void updateStatus(record, event.target.value as CaseStatus)}>{statuses.map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}</select></td><td>{formatDate(record.created_at)}</td><td>{formatDate(record.updated_at)}</td><td><button className="button-small" onClick={() => setSelected(record)}>Details</button></td></tr>;
            })}</tbody></table></div>
          )}
        </Panel>
      )}
      {selected && <CaseModal record={selected} onClose={() => setSelected(null)} />}
    </>
  );
}

function CaseModal({ record, onClose }: { record: CaseRecord; onClose: () => void }) {
  const [detail, setDetail] = useState<CaseRecord | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    api.case(record.id).then((item: CaseRecord) => { if (active) setDetail(item); }).catch((caught: unknown) => {
      if (active) setError(caught instanceof Error ? caught.message : "Could not load case details.");
    });
    return () => { active = false; };
  }, [record.id]);
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="detail-modal" role="dialog" aria-modal="true" aria-label="Case details">
        <div className="modal-head"><div><span className="eyebrow">INVESTIGATION RECORD</span><h2>{record.title}</h2></div><button className="button-quiet" aria-label="Close details" onClick={onClose}>×</button></div>
        {error ? <p className="error-copy">{error}</p> : !detail ? <LoadingState label="Loading case details…" /> : <>
          <div className="detail-meta"><span>CASE ID</span><code>{detail.id}</code><span>CREATED</span><b>{formatDate(detail.created_at)}</b></div>
          <div className="detail-meta"><span>STATUS</span><b>{detail.status.replaceAll("_", " ")}</b><span>PRIORITY</span><b>{detail.priority}</b></div>
          <p className="modal-description">{detail.description || "No case description was provided."}</p>
          <h3 className="modal-section-title">Analyst notes</h3>
          {detail.notes?.length ? <div className="note-list">{detail.notes.map((note) => <article key={note.id}><b>{note.author}</b><small>{formatDate(note.created_at)}</small><p>{note.content}</p></article>)}</div> : <p className="muted">No notes have been added to this case.</p>}
        </>}
      </section>
    </div>
  );
}
