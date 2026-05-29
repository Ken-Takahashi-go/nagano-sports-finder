/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'www.city.nagano.nagano.jp' },
    ],
  },
};

module.exports = nextConfig;
