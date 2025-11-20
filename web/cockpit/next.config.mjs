/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8002/api/:path*', // Proxy to FastAPI on port 8002
      },
    ];
  },
};

export default nextConfig;
