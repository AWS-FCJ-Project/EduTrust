# AWS Amplify Migration Summary

## What Changed

### Configuration Files

#### 1. `next.config.ts`
**Before**:
```typescript
const nextConfig = {
  output: "export", // Static export only
};
```

**After**:
```typescript
const nextConfig = {
  // Removed output: "export" to enable SSR
  images: {
    formats: ['image/avif', 'image/webp'],
  },
  experimental: {
    reactCompiler: true,
  },
  compress: true,
  poweredByHeader: false,
};
```

**Why**: Enable Server-Side Rendering and optimize for production.

---

#### 2. `amplify.yml` (New)
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

**Why**: Configure Amplify build process for Next.js SSR.

---

### Code Changes

#### 3. Dynamic Route: `/dashboard/bai-thi/[id]/page.tsx`
**Before**:
```typescript
export default function Page() {
  return <ExamPage />;
}
```

**After**:
```typescript
// Force dynamic rendering for user-specific exam data
export const dynamic = 'force-dynamic';
export const revalidate = 0;

export default function Page() {
  return <ExamPage />;
}
```

**Why**: Ensure real-time data for exam taking (no caching).

---

#### 4. API Configuration: `lib/api-config.ts` (New)
```typescript
export function getApiUrl(): string {
  const url = process.env.NEXT_PUBLIC_API_URL;
  if (!url) {
    throw new Error('API URL not configured');
  }
  return url;
}

export function createFetchOptions(token?: string): RequestInit {
  return {
    headers: {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
    },
  };
}
```

**Why**: Centralize API configuration and error handling.

---

#### 5. Dashboard Page: `dashboard/page.tsx`
**Before**:
```typescript
const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/user-info`, {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

**After**:
```typescript
const response = await fetch(`${getApiUrl()}/user-info`, {
  ...createFetchOptions(token),
  cache: 'no-store' // No caching for user data
});
```

**Why**: Use helper functions and explicit cache control.

---

### Workflow Changes

#### 6. `.github/workflows/app.yml`
**Before**:
```yaml
- name: Sync to S3
  run: aws s3 sync frontend/out/ s3://$S3_BUCKET --delete

- name: Invalidate CloudFront cache
  run: aws cloudfront create-invalidation --distribution-id $CLOUDFRONT_DIST_ID
```

**After**:
```yaml
- name: Skip Frontend Deployment
  run: |
    echo "Frontend is now deployed via AWS Amplify"
    echo "Amplify automatically deploys on git push"
```

**Why**: Amplify handles deployment automatically.

---

## Caching Strategy

### Page-Level Caching

| Page | Strategy | Revalidate | Reason |
|------|----------|------------|--------|
| `/` (Landing) | Static | 3600s | Marketing content |
| `/login` | Static | - | Auth page |
| `/dashboard` | Client SSR | 0s | User-specific |
| `/dashboard/bai-thi/[id]` | Force Dynamic | 0s | Real-time exam |
| `/dashboard/danh-sach-bai-thi` | ISR | 60s | Semi-dynamic list |

### API Call Caching

```typescript
// Static content (rarely changes)
fetch(url, { cache: 'force-cache' })

// ISR content (updates periodically)
fetch(url, { next: { revalidate: 60 } })

// Dynamic content (user-specific)
fetch(url, { cache: 'no-store' })
```

---

## Cost Comparison

### Before (S3 + CloudFront)
- Storage: $0.023/GB
- Data transfer: $0.085/GB
- Requests: $0.0004/1000
- **Total**: ~$1-2/month

### After (AWS Amplify)
- Build minutes: $0.01/minute
- Hosting: $0.15/GB served
- Storage: $0.023/GB
- **Total**: ~$4-5/month

### Cost Breakdown (Production)
```
20 deploys × 7 min = 140 minutes = $1.40
20GB served = $3.00
0.1GB storage = $0.002
─────────────────────────────────────
Total: $4.40/month
```

---

## Benefits

### Technical Benefits
1. ✅ **Dynamic Routes**: `/dashboard/bai-thi/[id]` works natively
2. ✅ **SSR Support**: Server-side rendering for SEO
3. ✅ **ISR**: Incremental Static Regeneration for performance
4. ✅ **Auto Deploy**: Push to git → automatic deployment
5. ✅ **Built-in CDN**: Global edge locations
6. ✅ **SSL/HTTPS**: Automatic certificate management
7. ✅ **Preview Deployments**: PR previews automatically

### Developer Experience
1. ✅ **No Manual Workflow**: Amplify deploys on push
2. ✅ **Easy Rollbacks**: One-click rollback in console
3. ✅ **Build Logs**: Detailed logs in Amplify Console
4. ✅ **Environment Variables**: Easy management in UI
5. ✅ **Monitoring**: Built-in performance metrics

---

## Migration Steps Completed

- [x] Remove `output: "export"` from next.config.ts
- [x] Add Amplify configuration (amplify.yml)
- [x] Update dynamic routes with proper caching
- [x] Create API configuration helper
- [x] Update fetch calls with cache control
- [x] Update workflow to skip S3 deployment
- [x] Create deployment documentation
- [x] Create refactoring examples
- [x] Update workflow README

---

## Next Steps

### 1. Setup AWS Amplify

1. Go to [AWS Amplify Console](https://console.aws.amazon.com/amplify/)
2. Click "New app" → "Host web app"
3. Connect GitHub repository
4. Select branch (main or feat/Data-Infastructure)
5. Amplify auto-detects Next.js configuration
6. Add environment variable: `NEXT_PUBLIC_API_URL`
7. Click "Save and deploy"

### 2. Verify Deployment

1. Wait for build to complete (~5-7 minutes)
2. Visit provided URL: `https://xxx.amplifyapp.com`
3. Test dynamic routes: `/dashboard/bai-thi/123`
4. Verify API calls work correctly
5. Check authentication flow

### 3. Monitor Performance

1. Check Amplify Console → Monitoring
2. Review build logs for errors
3. Monitor request latency
4. Track data transfer costs

### 4. Optimize (Optional)

1. Increase ISR revalidate times if acceptable
2. Convert more pages to static if possible
3. Optimize images with Next.js Image component
4. Enable React Compiler for better performance

---

## Troubleshooting

### Build Fails

**Issue**: `npm ci` fails with peer dependency errors
**Solution**: Use `npm ci --legacy-peer-deps` (already in amplify.yml)

**Issue**: Environment variable not found
**Solution**: Add `NEXT_PUBLIC_API_URL` in Amplify Console → Environment variables

### Runtime Errors

**Issue**: API calls return 404
**Solution**: Verify `NEXT_PUBLIC_API_URL` is set correctly in Amplify

**Issue**: Dynamic routes return 404
**Solution**: Amplify automatically handles Next.js rewrites - check build logs

**Issue**: Authentication not working
**Solution**: Verify cookies are set with correct domain and secure flags

### Performance Issues

**Issue**: Slow page loads
**Solution**: 
1. Check caching strategy (use ISR when possible)
2. Verify revalidate times are appropriate
3. Consider reducing SSR usage

---

## Rollback Plan

If Amplify deployment fails:

1. **Quick Rollback**: 
   - Go to Amplify Console → Deployments
   - Find previous successful deployment
   - Click "Redeploy this version"

2. **Full Rollback to S3**:
   - Revert `next.config.ts` to add `output: "export"`
   - Revert workflow to use S3 deployment
   - Push changes to trigger S3 deployment

---

## Support Resources

- [AWS Amplify Documentation](https://docs.amplify.aws/)
- [Next.js Deployment Guide](https://nextjs.org/docs/deployment)
- [Amplify Pricing Calculator](https://aws.amazon.com/amplify/pricing/)
- Project Documentation: `frontend/AMPLIFY_DEPLOYMENT.md`
- Refactoring Examples: `frontend/REFACTORING_EXAMPLES.md`

---

## Success Criteria

- [ ] Amplify app created and connected to GitHub
- [ ] Environment variables configured
- [ ] Build completes successfully
- [ ] Application accessible via Amplify URL
- [ ] Dynamic routes work correctly
- [ ] API calls succeed
- [ ] Authentication flow works
- [ ] Performance is acceptable
- [ ] Costs are within budget

---

## Conclusion

The migration from S3 static hosting to AWS Amplify SSR enables:
- Full support for dynamic routes
- Better SEO with server-side rendering
- Automatic deployments on git push
- Improved developer experience
- Production-ready architecture

The slight cost increase ($3-4/month) is justified by the significant improvements in functionality and developer productivity.
