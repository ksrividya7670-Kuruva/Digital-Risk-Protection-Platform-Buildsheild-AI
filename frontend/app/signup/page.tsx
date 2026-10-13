"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

function strengthLabel(pw: string): { label: string; level: number } {
  if (!pw) return { label: "", level: 0 };
  let score = 0;
  if (pw.length >= 8)  score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  const labels = ["", "Weak", "Fair", "Good", "Strong", "Strong"];
  return { label: labels[score] ?? "Strong", level: score };
}

export default function SignupPage() {
  const router = useRouter();
  const [fullName, setFullName]       = useState("");
  const [email, setEmail]             = useState("");
  const [password, setPassword]       = useState("");
  const [confirmPw, setConfirmPw]     = useState("");
  const [showPw, setShowPw]           = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState("");

  const strength = strengthLabel(password);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!fullName.trim()) { setError("Please enter your full name."); return; }
    if (!email.trim())    { setError("Please enter your email address."); return; }
    if (password.length < 8) { setError("Password must be at least 8 characters."); return; }
    if (password !== confirmPw) { setError("Passwords do not match."); return; }
    setLoading(true);
    await new Promise(r => setTimeout(r, 1000));
    localStorage.setItem("brandshield_auth", "true");
    localStorage.setItem("brandshield_user", email);
    localStorage.setItem("brandshield_name", fullName.trim());
    setLoading(false);
    router.push("/dashboard");
  }

  return (
    <main className="login-screen">
      <div className="login-ambient" />

      <div className="login-brand">
        <Image src="/Futuristic%20BrandShield-AI%20Neon%20Logo.png" alt="BrandShield AI" width={64} height={64} priority />
        <div>
          <strong>BrandShield <em>AI</em></strong>
          <small>DIGITAL RISK PROTECTION</small>
        </div>
      </div>

      <section className="login-card">
        <span className="login-kicker"><i />CREATE ANALYST ACCOUNT</span>
        <h1>Create account</h1>
        <p>Set up your security operations workspace.</p>

        {error && <div className="login-error" role="alert">{error}</div>}

        <form onSubmit={handleSubmit} noValidate>
          <label htmlFor="su-name">Full name</label>
          <input
            id="su-name"
            type="text"
            autoComplete="name"
            placeholder="Jane Smith"
            value={fullName}
            onChange={e => setFullName(e.target.value)}
            required
          />

          <label htmlFor="su-email">Email address</label>
          <input
            id="su-email"
            type="email"
            autoComplete="email"
            placeholder="analyst@company.com"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
          />

          <label htmlFor="su-pw">Password <span className="opt-tag">{strength.label}</span></label>
          <div className="pw-wrap">
            <input
              id="su-pw"
              type={showPw ? "text" : "password"}
              autoComplete="new-password"
              placeholder="Create a strong password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              minLength={8}
            />
            <button type="button" className="pw-toggle" onClick={() => setShowPw(v => !v)} aria-label={showPw ? "Hide password" : "Show password"}>
              {showPw ? "◕" : "○"}
            </button>
          </div>
          {password && (
            <div className="pw-strength" aria-label={`Password strength: ${strength.label}`}>
              {[1,2,3,4,5].map(n => (
                <span key={n} className={`pw-bar ${n <= strength.level ? `pw-bar-${Math.min(strength.level, 3) >= 3 ? "strong" : strength.level >= 2 ? "fair" : "weak"}` : ""}`} />
              ))}
            </div>
          )}

          <label htmlFor="su-confirm">Confirm password</label>
          <div className="pw-wrap">
            <input
              id="su-confirm"
              type={showConfirm ? "text" : "password"}
              autoComplete="new-password"
              placeholder="Repeat your password"
              value={confirmPw}
              onChange={e => setConfirmPw(e.target.value)}
              required
            />
            <button type="button" className="pw-toggle" onClick={() => setShowConfirm(v => !v)} aria-label={showConfirm ? "Hide password" : "Show password"}>
              {showConfirm ? "◕" : "○"}
            </button>
          </div>

          <button className="button-primary login-submit" type="submit" disabled={loading}>
            {loading ? <><span className="btn-spinner" />Creating account…</> : <>Create account <span>→</span></>}
          </button>
        </form>

        <p className="login-note">
          Already have an account?{" "}
          <Link href="/login" className="login-link">Sign in →</Link>
        </p>
      </section>

      <footer className="login-footer">
        BRANDSHIELD AI <span>·</span> SECURITY OPERATIONS <span>·</span> SOC CONSOLE
      </footer>
    </main>
  );
}
