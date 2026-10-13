"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const navigation = [
  { href: "/dashboard", label: "Dashboard",    icon: "⌂" },
  { href: "/threats",   label: "Threat queue", icon: "⌁" },
  { href: "/analyze",   label: "Analyze",      icon: "⚡" },
  { href: "/brands",    label: "Brands",        icon: "◈" },
  { href: "/cases",     label: "Cases",         icon: "▤" },
  { href: "/analytics", label: "Analytics",    icon: "▥" },
];

function logout() {
  localStorage.removeItem("brandshield_auth");
  localStorage.removeItem("brandshield_user");
  localStorage.removeItem("brandshield_name");
  window.location.href = "/";
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [toast, setToast] = useState<{ message: string; tone: string } | null>(null);

  // Fix SSR hydration: read localStorage only on the client after mount
  const [userName, setUserName]     = useState("Security Analyst");
  const [userEmail, setUserEmail]   = useState("analyst@brandshield.ai");
  const [userInitials, setUserInitials] = useState("SA");

  useEffect(() => {
    const name  = localStorage.getItem("brandshield_name")  || "Security Analyst";
    const email = localStorage.getItem("brandshield_user")  || "analyst@brandshield.ai";
    setUserName(name);
    setUserEmail(email);
    const initials = name.split(" ").map((w: string) => w[0] ?? "").join("").toUpperCase().slice(0, 2) || "SA";
    setUserInitials(initials);
  }, []);

  // Close user menu when clicking outside
  useEffect(() => {
    if (!userMenuOpen) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Element;
      if (!target.closest(".profile-menu-container")) setUserMenuOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [userMenuOpen]);

  // Toast system
  useEffect(() => {
    const receive = (event: Event) => {
      const detail = (event as CustomEvent<{ message: string; tone: string }>).detail;
      setToast(detail);
      window.setTimeout(() => setToast(null), 3800);
    };
    window.addEventListener("brandshield:toast", receive);
    return () => window.removeEventListener("brandshield:toast", receive);
  }, []);

  const title =
    navigation.find(
      (item) =>
        pathname === item.href ||
        (item.href === "/threats"  && pathname.startsWith("/candidates")) ||
        (item.href === "/analyze"  && pathname === "/analyze"),
    )?.label ?? "Security operations";

  return (
    <div className="app-frame">
      {/* Mobile backdrop */}
      {mobileOpen && (
        <button
          className="mobile-scrim"
          type="button"
          aria-label="Close navigation"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* ── Sidebar ──────────────────────── */}
      <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
        <Link href="/dashboard" className="brand-lockup" onClick={() => setMobileOpen(false)}>
          <Image
            src="/Futuristic%20BrandShield-AI%20Neon%20Logo.png"
            alt="BrandShield AI"
            width={44}
            height={44}
            priority
            className="brand-logo"
          />
          <span>
            <strong>BrandShield <em>AI</em></strong>
            <small>THREAT INTELLIGENCE</small>
          </span>
        </Link>

        <div className="sidebar-section-label">WORKSPACE</div>

        <nav className="side-nav" aria-label="Main navigation">
          {navigation.map((item) => {
            const active =
              pathname === item.href ||
              (item.href === "/threats" && pathname.startsWith("/candidates"));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`nav-link ${active ? "nav-link-active" : ""}`}
                onClick={() => setMobileOpen(false)}
              >
                <span className="nav-icon" aria-hidden="true">{item.icon}</span>
                <span>{item.label}</span>
                {item.href === "/threats" && <span className="nav-live-dot" />}
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-bottom">
          <div className="demo-card">
            <span className="demo-indicator" />
            <span>
              <b>Demo environment</b>
              <small>Synthetic dataset</small>
            </span>
          </div>

          {/* Profile row */}
          <div className="profile-row">
            <div className="avatar" aria-hidden="true">{userInitials}</div>
            <span className="profile-info">
              <b>{userName}</b>
              <small>{userEmail}</small>
            </span>

            {/* User dropdown */}
            <div className="profile-menu-container">
              <button
                className="profile-menu"
                type="button"
                aria-label="User menu"
                aria-expanded={userMenuOpen}
                onClick={() => setUserMenuOpen(v => !v)}
              >
                •••
              </button>
              {userMenuOpen && (
                <div className="profile-dropdown" role="menu">
                  <div className="dropdown-header">
                    <div className="dropdown-avatar">{userInitials}</div>
                    <div>
                      <strong>{userName}</strong>
                      <small>{userEmail}</small>
                    </div>
                  </div>
                  <hr className="dropdown-separator" />
                  <Link href="/dashboard" className="dropdown-item" role="menuitem" onClick={() => setUserMenuOpen(false)}>
                    <span className="nav-icon">⌂</span>
                    <span>Dashboard</span>
                  </Link>
                  <Link href="/analytics" className="dropdown-item" role="menuitem" onClick={() => setUserMenuOpen(false)}>
                    <span className="nav-icon">▥</span>
                    <span>Analytics</span>
                  </Link>
                  <hr className="dropdown-separator" />
                  <button
                    className="dropdown-item dropdown-item-danger"
                    type="button"
                    role="menuitem"
                    onClick={logout}
                  >
                    <span className="nav-icon">↩</span>
                    <span>Sign out</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </aside>

      {/* ── Main column ──────────────────── */}
      <div className="main-column">
        <header className="topbar">
          <button
            className="mobile-menu button-quiet"
            type="button"
            aria-label="Open navigation"
            onClick={() => setMobileOpen(true)}
          >
            ☰
          </button>
          <div className="breadcrumb">
            <span>BrandShield AI</span><b>/</b>{title}
          </div>
          <div className="topbar-right">
            <span className="system-state"><i /> SYSTEM OPERATIONAL</span>
            <span className="topbar-divider" />
            <span className="utc-time">SOC · DEMO</span>
            <span className="topbar-divider" />
            <button
              className="topbar-logout"
              type="button"
              onClick={logout}
              aria-label="Sign out"
            >
              ↩ Sign out
            </button>
          </div>
        </header>
        <main className="page-content">{children}</main>
      </div>

      {/* Toast */}
      {toast && (
        <div className={`toast toast-${toast.tone}`} role="status" aria-live="polite">
          <span className="toast-icon">{toast.tone === "error" ? "✕" : "✓"}</span>
          {toast.message}
        </div>
      )}
    </div>
  );
}
