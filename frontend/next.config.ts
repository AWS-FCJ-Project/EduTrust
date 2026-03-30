import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // AWS Amplify SSR Configuration
  // Removed output: "export" to enable Server-Side Rendering
  
  // Optimize images for Amplify
  images: {
    formats: ['image/avif', 'image/webp'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
  },

  // Enable React Compiler for better performance
  experimental: {
    reactCompiler: true,
  },

  // Optimize production builds
  compress: true,
  poweredByHeader: false,

  // Logging configuration for CloudWatch
  logging: {
    fetches: {
      fullUrl: true,
    },
  },

  // Environment variable validation
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || '',
  },
};

export default nextConfig;
