/** @type {import('next').NextConfig} */
const API_BACKEND = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:18081";

const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_BACKEND}/api/:path*`,
      },
      {
        source: "/ws/:path*",
        destination: `${API_BACKEND}/ws/:path*`,
      },
      {
        source: "/uploads/:path*",
        destination: `${API_BACKEND}/uploads/:path*`,
      },
    ];
  },
};

export default nextConfig;
