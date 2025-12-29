/** @type {import('next').NextConfig} */
const nextConfig = {
  // Production: API calls go directly to backend
  // Development: Proxy to local backend
  async rewrites() {
    // In production, don't rewrite - frontend calls API directly
    if (process.env.NODE_ENV === 'production') {
      return []
    }

    // Development proxy
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.BACKEND_URL || 'http://localhost:8000'}/:path*`,
      },
    ]
  },

  // Security headers
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-DNS-Prefetch-Control', value: 'on' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
        ],
      },
    ]
  },
}

module.exports = nextConfig
