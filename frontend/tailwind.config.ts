import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // BrandShield AI design tokens
        // Dark security theme
        surface: {
          DEFAULT: "#0f1117",
          raised: "#161b27",
          overlay: "#1e2535",
        },
        brand: {
          DEFAULT: "#06b6d4",  // cyan-500
          dark: "#0891b2",
        },
        risk: {
          critical: "#ef4444",  // red-500
          high: "#f97316",      // orange-500
          medium: "#eab308",    // yellow-500
          low: "#22c55e",       // green-500
        },
      },
    },
  },
  plugins: [],
};

export default config;
