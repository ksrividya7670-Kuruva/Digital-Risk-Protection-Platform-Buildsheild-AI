"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw]     = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password) { setError("Please enter your email and password."); return; }
    setError("");
    setLoading(true);
    await new Promise(r => setTimeout(r, 900));

    const name =
      email === "analyst@brandshield.demo" ? "Demo Analyst"
      : email.split("@")[0].replace(/[._-]/g, " ").replace(/\b\w/g, c => c.toUpperCase());

    localStorage.setItem("brandshield_auth", "true");
    localStorage.setItem("brandshield_user", email);
    localStorage.setItem("brandshield_name", name);
    setLoading(false);
    router.push("/dashboard");
  }

  function enterDemo() {
    localStorage.setItem("brandshield_auth", "true");
    localStorage.setItem("brandshield_user", "analyst@brandshield.demo");
    localStorage.setItem("brandshield_name", "Demo Analyst");
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
        <span className="login-kicker"><i />SOC ANALYST ACCESS</span>
        <h1>Sign in</h1>
        <p>Access your digital risk protection workspace.</p>

        {error && <div className="login-error" role="alert">{error}</div>}

        <form onSubmit={handleLogin} noValidate>
          <label htmlFor="login-email">Email address</label>
          <input
            id="login-email"
            type="email"
            autoComplete="email"
            placeholder="analyst@company.com"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
          />

          <label htmlFor="login-pw">Password</label>
          <div className="pw-wrap">
            <input
              id="login-pw"
              type={showPw ? "text" : "password"}
              autoComplete="current-password"
              placeholder="Enter your password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
            <button type="button" className="pw-toggle" onClick={() => setShowPw(v => !v)} aria-label={showPw ? "Hide password" : "Show password"}>
              {showPw ? "◕" : "○"}
            </button>
          </div>

          <button className="button-primary login-submit" type="submit" disabled={loading}>
            {loading ? <><span className="btn-spinner" />Signing in…</> : <>Sign in <span>→</span></>}
          </button>
        </form>

        <div className="login-separator"><span /><span>OR</span><span /></div>

        <button className="button-secondary demo-entry" onClick={enterDemo} type="button">
          <span className="demo-indicator" />
          Enter demo mode
          <span>→</span>
        </button>

        <div className="demo-credentials">
          <strong>Demo credentials</strong>
          <div>analyst@brandshield.demo</div>
          <div>BrandShield@123</div>
        </div>

        <p className="login-note">
          Don&apos;t have an account?{" "}
          <Link href="/signup" className="login-link">Create account →</Link>
        </p>
      </section>

      <footer className="login-footer">
        BRANDSHIELD AI <span>·</span> DIGITAL RISK PROTECTION <span>·</span> SOC CONSOLE
      </footer>
    </main>
  );
}
