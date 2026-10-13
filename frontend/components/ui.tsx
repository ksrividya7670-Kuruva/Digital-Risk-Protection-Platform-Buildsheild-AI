import Link from "next/link";
import type { RiskLevel } from "@/lib/api";

export function PageHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {action && <div className="heading-action">{action}</div>}
    </div>
  );
}

export function Panel({
  title,
  subtitle,
  action,
  children,
  className = "",
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

export function RiskBadge({ level }: { level: string | null | undefined }) {
  const normalized = (level ?? "UNASSESSED").toLowerCase();
  return <span className={`risk-badge risk-${normalized}`}>{level ?? "UNASSESSED"}</span>;
}

export function StatCard({
  label,
  value,
  detail,
  tone = "cyan",
  icon,
}: {
  label: string;
  value: string | number;
  detail?: string;
  tone?: "cyan" | "red" | "orange" | "yellow" | "green";
  icon: string;
}) {
  return (
    <div className={`stat-card stat-${tone}`}>
      <div className="stat-top"><span>{label}</span><span className="stat-icon">{icon}</span></div>
      <div className="stat-value">{value}</div>
      {detail && <div className="stat-detail">{detail}</div>}
    </div>
  );
}

export function LoadingState({ label = "Loading live data…" }: { label?: string }) {
  return (
    <div className="loading-state" role="status">
      <span className="spinner" />{label}
    </div>
  );
}

export function ErrorState({
  message,
  retry,
}: {
  message: string;
  retry?: () => void;
}) {
  return (
    <div className="error-state" role="alert">
      <span className="error-icon">!</span>
      <div><b>Unable to load this view</b><p>{message}</p></div>
      {retry && <button className="button-secondary" onClick={retry}>Try again</button>}
    </div>
  );
}

export function EmptyState({
  title,
  detail,
  href,
  action,
}: {
  title: string;
  detail: string;
  href?: string;
  action?: string;
}) {
  const body = (
    <>
      <div className="empty-mark">◌</div>
      <b>{title}</b>
      <p>{detail}</p>
    </>
  );
  return (
    <div className="empty-state">
      {href && action ? <Link className="button-primary" href={href}>{action}</Link> : null}
      {body}
    </div>
  );
}

export function SignalBar({
  label,
  value,
  max,
}: {
  label: string;
  value: number;
  max: number;
}) {
  const percent = max > 0 ? Math.min(100, Math.max(0, (value / max) * 100)) : 0;
  return (
    <div className="signal-row">
      <div className="signal-label"><span>{label}</span><b>{value.toFixed(1)} <small>/ {max}</small></b></div>
      <div className="signal-track"><span style={{ width: `${percent}%` }} /></div>
    </div>
  );
}

export function levelTone(level: RiskLevel | null) {
  return level ? `risk-${level.toLowerCase()}` : "risk-unassessed";
}
