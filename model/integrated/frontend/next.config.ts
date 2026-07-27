import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
    const modelApiBaseUrl = process.env.NEXT_PUBLIC_MODEL_API_BASE_URL;
    const rewrites = [];

    if (apiBaseUrl) {
      const normalizedApiBaseUrl = apiBaseUrl.replace(/\/+$/, "");

      rewrites.push({
        source: "/api/:path*",
        destination: `${normalizedApiBaseUrl}/api/:path*`,
      });

      rewrites.push({
        source: "/uploads/:path*",
        destination: `${normalizedApiBaseUrl}/uploads/:path*`,
      });
    }

    if (modelApiBaseUrl) {
      rewrites.push({
        source: "/model-api/:path*",
        destination: `${modelApiBaseUrl.replace(/\/+$/, "")}/:path*`,
      });
    }

    return rewrites;
  },
};

export default nextConfig;
