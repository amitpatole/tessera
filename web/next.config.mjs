/** @type {import('next').NextConfig} */
const nextConfig = {
  // Lint is run in CI/locally via `next lint`; don't fail the production build on it.
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
