/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  transpilePackages: [],
  eslint: {
    // ESLint 检查仅在本地开发时运行，Docker build 时跳过以加快构建速度
    ignoreDuringBuilds: true,
  },
  env: {
    NEXT_PUBLIC_API_URL: '',
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.API_URL || 'http://host.docker.internal:8000'}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
