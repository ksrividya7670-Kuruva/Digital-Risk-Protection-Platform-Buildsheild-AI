"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const auth = localStorage.getItem('brandshield_auth');
      const authenticated = !!auth;
      
      setIsAuthenticated(authenticated);
      
      if (!authenticated) {
        router.push('/');
      }
    }
  }, [router]);

  if (isAuthenticated === null) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner" />
        <p>Loading...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}