"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    if (typeof window !== "undefined" && localStorage.getItem("brandshield_auth")) {
      router.replace("/dashboard");
    }
  }, [router]);

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
        <Image
          src="/Futuristic%20BrandShield-AI%20Neon%20Logo.png"
          alt="BrandShield AI"
          width={64}
          height={64}
          priority
        />
        <div>
          <strong>BrandShield <em>AI</em></strong>
          <small>DIGITAL RISK PROTECTION</small>
        </div>
      </div>

      <section className="login-card">
        <span className="login-kicker"><i />AUTONOMOUS THREAT DETECTION</span>
        <h1>BrandShield AI</h1>
        <p>AI-powered protection against social media impersonation and rogue mobile apps.</p>

        <div className="feature-grid">
          <div><span>◈</span>Explainable Risk Scoring</div>
          <div><span>◎</span>Social Impersonation Detection</div>
          <div><span>▣</span>Mobile App Monitoring</div>
          <div><span>▤</span>Case Management</div>
        </div>

        <button className="button-primary demo-entry" onClick={enterDemo}>
          <span className="demo-indicator" />
          Enter Demo
          <span>→</span>
        </button>

        <button className="button-secondary login-submit" onClick={() => router.push("/login")}>
          Sign In <span>→</span>
        </button>

        <button className="button-secondary login-submit" onClick={() => router.push("/signup")}>
          Create Account <span>→</span>
        </button>

        <p className="login-note">Synthetic data only · No real accounts or personal information</p>
      </section>

      <footer className="login-footer">
        BRANDSHIELD AI <span>·</span> HACKATHON DEMO <span>·</span> DIGITAL RISK PROTECTION
      </footer>
    </main>
  );
}
