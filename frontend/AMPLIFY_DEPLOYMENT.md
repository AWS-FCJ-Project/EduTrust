# AWS Amplify Deployment Guide

## Overview

This Next.js application is optimized for AWS Amplify deployment with Server-Side Rendering (SSR) and Incremental Static Regeneration (ISR) support.

## Architecture Changes

### Removed
- ❌ `output: "export"` - Static export mode
- ❌ `generateStaticParams()` - Unnecessary for dynamic routes with SSR
- ❌ S3 + CloudFront static hosting

### Added
- ✅ AWS Amplify SSR support
- ✅ Dynamic route handling with proper caching strategies
- ✅ Optimized data fetching patterns
- ✅ Environment variable management
- ✅ Production-ready error handling

## Data Fetching Strategies

### 1. Static Pages (Landing, About, etc.)
**Use Case**: Content that rarely changes
**Strategy**: Static Generation with ISR

```typescript
// app/page.tsx
export const revalidate = 3600; // Revalidate every hour

export default function HomePage() {
  return <div>Static content</div>;
}
```

### 2. ISR Pages (Exam List, Resources)
**Use Case**: Content that changes periodically
**Strategy**: Incremental Static Regeneration

```typescript
// app/dashboard/danh-sach-bai-thi/page.tsx
export const revalidate = 60; // Revalidate every 60 seconds

export default async function ExamListPage() {
  // Server-side data fetching with ISR
  const exams = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/exams`, {
    next: { revalidate: 60 }
  }).then(res => res.json());

  return <ExamList exams={exams} />;
}
```

### 3. Dynamic Pages (User Dashboard, Exam Taking)
**Use Case**: User-specific or real-time data
**Strategy**: Server-Side Rendering (SSR)

```typescript
// app/dashboard/bai-thi/[id]/page.tsx
export const dynamic = 'force-dynamic';
export const revalidate = 0;

export default function ExamPage() {
  // Client-side fetching for authenticated data
  return <ExamPageClient />;
}
```

### 4. Client-Side Fetching (Current Implementation)
**Use Case**: Authenticated user data
**Strategy**: Client-side with proper cache control

```typescript
// Using the API helper
import { getApiUrl, createFetchOptions } from '@/lib/api-config';
import Cookies from 'js-cookie';

const token = Cookies.get('auth_token');
const response = await fetch(`${getApiUrl()}/user-info`, {
  ...createFetchOptions(token),
  cache: 'no-store' // No caching for user-specific data
});
```

## Caching Strategy Matrix

| Page Type | Strategy | Revalidate | Cache | Use Case |
|-----------|----------|------------|-------|----------|
| Landing | Static | 3600s | force-cache | Marketing pages |
| Exam List | ISR | 60s | revalidate | Semi-dynamic content |
| User Dashboard | SSR | 0s | no-store | User-specific data |
| Exam Taking | Dynamic | 0s | no-store | Real-time interaction |
| Login | Static | - | force-cache | Auth page |

## Environment Variables

### Required Variables

Add these in AWS Amplify Console → Environment variables:

```bash
NEXT_PUBLIC_API_URL=https://your-backend-alb-url.com
```

### Local Development

Create `.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Cost Optimization

### Minimize SSR Usage

1. **Use ISR for semi-dynamic content** (exam lists, resources)
2. **Use Static for marketing pages** (landing, about)
3. **Reserve SSR for user-specific data** (dashboard, exam taking)

### Expected Costs

**Development (Free Tier)**:
- Build minutes: 1000/month (FREE)
- Data served: 15GB/month (FREE)
- Storage: 5GB (FREE)

**Production**:
- ~20 deploys/month × 7 min = 140 minutes = $1.40
- ~20GB served = $3.00
- Total: **~$4.40/month**

## Deployment Steps

### 1. Push Code to GitHub

```bash
git add .
git commit -m "refactor: Optimize for AWS Amplify SSR deployment"
git push origin main
```

### 2. Create Amplify App

1. Go to [AWS Amplify Console](https://console.aws.amazon.com/amplify/)
2. Click "New app" → "Host web app"
3. Connect GitHub repository
4. Select branch (main or feat/Data-Infastructure)
5. Amplify auto-detects Next.js configuration

### 3. Configure Build Settings

Amplify will use `amplify.yml`:

```yaml
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - cd frontend
        - npm ci --legacy-peer-deps
    build:
      commands:
        - npm run build
  artifacts:
    baseDirectory: frontend/.next
    files:
      - '**/*'
  cache:
    paths:
      - frontend/node_modules/**/*
      - frontend/.next/cache/**/*
```

### 4. Add Environment Variables

In Amplify Console → App settings → Environment variables:

```
NEXT_PUBLIC_API_URL = https://your-backend-url.com
```

### 5. Deploy

Click "Save and deploy" - Amplify will:
1. Clone repository
2. Install dependencies
3. Build Next.js app
4. Deploy to CDN
5. Provide URL: `https://xxx.amplifyapp.com`

## Monitoring

### Build Logs

Check Amplify Console → Build history for:
- Build duration
- Error messages
- Deployment status

### Performance

Monitor in Amplify Console → Monitoring:
- Request count
- Error rate
- Latency
- Data transfer

## Troubleshooting

### Build Fails

**Issue**: `npm ci` fails
**Solution**: Use `npm ci --legacy-peer-deps` in amplify.yml

**Issue**: Environment variable not found
**Solution**: Add `NEXT_PUBLIC_API_URL` in Amplify Console

### Runtime Errors

**Issue**: API calls fail
**Solution**: Verify `NEXT_PUBLIC_API_URL` is set correctly

**Issue**: 404 on dynamic routes
**Solution**: Amplify automatically handles Next.js rewrites

### Performance Issues

**Issue**: Slow page loads
**Solution**: 
1. Check if using correct caching strategy
2. Verify ISR revalidation times
3. Consider reducing SSR usage

## Migration from S3

### What Changed

| Before (S3) | After (Amplify) |
|-------------|-----------------|
| Static export only | SSR + ISR support |
| Manual workflow | Auto-deploy on push |
| No dynamic routes | Full dynamic support |
| CloudFront manual | Automatic CDN |
| $1-2/month | $4-5/month |

### Benefits

1. ✅ Dynamic routes work natively
2. ✅ Server-side rendering for SEO
3. ✅ Automatic deployments
4. ✅ Built-in CDN and SSL
5. ✅ Easy rollbacks
6. ✅ Preview deployments for PRs

## Best Practices

### 1. Cache Appropriately

```typescript
// ❌ Bad: SSR for static content
export const dynamic = 'force-dynamic';

// ✅ Good: ISR for semi-dynamic content
export const revalidate = 60;
```

### 2. Handle Errors Gracefully

```typescript
try {
  const data = await fetch(url);
} catch (error) {
  console.error('API Error:', error);
  // Show user-friendly error message
}
```

### 3. Validate Environment Variables

```typescript
if (!process.env.NEXT_PUBLIC_API_URL) {
  throw new Error('API URL not configured');
}
```

### 4. Use Proper Loading States

```typescript
if (loading) return <Loader />;
if (error) return <ErrorMessage />;
return <Content data={data} />;
```

## Support

For issues:
1. Check [AWS Amplify Docs](https://docs.amplify.aws/)
2. Review build logs in Amplify Console
3. Verify environment variables
4. Check API connectivity

## Rollback

If deployment fails:
1. Go to Amplify Console → Deployments
2. Find previous successful deployment
3. Click "Redeploy this version"
