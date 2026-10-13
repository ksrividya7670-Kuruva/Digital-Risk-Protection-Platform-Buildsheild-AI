/** @type {import('next').NextConfig} */
const isStatic = process.env.NEXT_PUBLIC_STATIC_MODE === "true";

const repoName = process.env.GITHUB_REPOSITORY
  ? `/${process.env.GITHUB_REPOSITORY.split("/")[1]}`
  : "/Digital-Risk-Protection-Platform-Buildsheild-AI";

const nextConfig = {
  // Static export for GitHub Pages
  ...(isStatic ? {
    output: "export",
    basePath: repoName,
    assetPrefix: `${repoName}/`,
    trailingSlash: true,
    images: { unoptimized: true },
  } : {
    // Dev / Vercel / Render: use API proxy rewrites
    async rewrites() {
      const backendUrl =
        process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
      return [
        { source: "/api/:path*", destination: `${backendUrl}/api/:path*` },
        { source: "/health",     destination: `${backendUrl}/health` },
      ];
    },
  }),
};

export default nextConfig;
