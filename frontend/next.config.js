/** @type {import('next').NextConfig} */
const isProduction = process.env.NODE_ENV === 'production'
const backendOrigin =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.RAILWAY_API_URL ||
  (isProduction ? null : 'http://localhost:8000')

if (!backendOrigin) {
  throw new Error(
    'Missing API origin. Set RAILWAY_API_URL or NEXT_PUBLIC_API_URL for production frontend builds.',
  )
}

const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${backendOrigin}/api/:path*`,
      },
      {
        source: '/health',
        destination: `${backendOrigin}/health`,
      },
    ]
  },
}

module.exports = nextConfig
