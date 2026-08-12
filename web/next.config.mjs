/** @type {import('next').NextConfig} */
const nextConfig = {
  // Pure static export — no server, no API routes. The dashboard is a
  // function of the JSON in public/data, written by `casita export`.
  output: "export",
  images: { unoptimized: true },
};

export default nextConfig;
