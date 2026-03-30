# Data Fetching Refactoring Examples

## Example 1: Static Page (Landing Page)

### Before (Client-Side Only)
```typescript
// app/page.tsx
"use client";

export default function Home() {
  return (
    <div>
      <Header />
      <Content />
      <Footer />
    </div>
  );
}
```

### After (Static with ISR)
```typescript
// app/page.tsx
import Header from "@/landing/Header";
import Footer from "@/landing/Footer";
import Content from "@/landing/Content";

// Revalidate every hour for marketing content updates
export const revalidate = 3600;

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <Content />
      <Footer />
    </div>
  );
}
```

**Benefits**:
- ✅ Static generation at build time
- ✅ ISR updates content hourly
- ✅ No SSR cost for every request
- ✅ Better SEO with pre-rendered HTML

---

## Example 2: ISR Page (Exam List)

### Before (Client-Side Fetching)
```typescript
// app/dashboard/danh-sach-bai-thi/page.tsx
"use client";

export default function ExamListPage() {
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/exams`)
      .then(res => res.json())
      .then(data => setExams(data))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader />;
  return <ExamList exams={exams} />;
}
```

### After (Server-Side with ISR)
```typescript
// app/dashboard/danh-sach-bai-thi/page.tsx
import { getApiUrl } from '@/lib/api-config';
import ExamListClient from './ExamListClient';

// Revalidate every 60 seconds
export const revalidate = 60;

async function getExams() {
  try {
    const res = await fetch(`${getApiUrl()}/exams/public`, {
      next: { revalidate: 60 }
    });
    
    if (!res.ok) return [];
    return await res.json();
  } catch (error) {
    console.error('Failed to fetch exams:', error);
    return [];
  }
}

export default async function ExamListPage() {
  const exams = await getExams();
  
  return <ExamListClient initialExams={exams} />;
}
```

```typescript
// app/dashboard/danh-sach-bai-thi/ExamListClient.tsx
"use client";

import { useState, useEffect } from 'react';
import Cookies from 'js-cookie';
import { getApiUrl, createFetchOptions } from '@/lib/api-config';

export default function ExamListClient({ initialExams }: { initialExams: any[] }) {
  const [exams, setExams] = useState(initialExams);
  const [loading, setLoading] = useState(false);

  // Fetch user-specific exam status on client
  useEffect(() => {
    const fetchUserExamStatus = async () => {
      const token = Cookies.get('auth_token');
      if (!token) return;

      setLoading(true);
      try {
        const res = await fetch(
          `${getApiUrl()}/exams/user-status`,
          createFetchOptions(token, { cache: 'no-store' })
        );
        
        if (res.ok) {
          const userStatus = await res.json();
          // Merge user status with initial exams
          setExams(prev => prev.map(exam => ({
            ...exam,
            ...userStatus.find((s: any) => s.id === exam.id)
          })));
        }
      } catch (error) {
        console.error('Failed to fetch user status:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchUserExamStatus();
  }, []);

  return <ExamList exams={exams} loading={loading} />;
}
```

**Benefits**:
- ✅ Server renders exam list (SEO friendly)
- ✅ ISR updates every 60 seconds
- ✅ Client-side hydration for user-specific data
- ✅ Reduced SSR cost (cached for 60s)

---

## Example 3: Dynamic Page (Exam Taking)

### Before (Client-Side Only)
```typescript
// app/dashboard/bai-thi/[id]/page.tsx
import ExamPage from "./ExamPage";

export default function Page() {
  return <ExamPage />;
}
```

### After (Force Dynamic)
```typescript
// app/dashboard/bai-thi/[id]/page.tsx
import ExamPage from "./ExamPage";

// Force dynamic rendering for real-time exam data
export const dynamic = 'force-dynamic';
export const revalidate = 0;

export default function Page() {
  return <ExamPage />;
}
```

**Benefits**:
- ✅ Always fresh data for exam taking
- ✅ No caching for security
- ✅ Proper handling of user-specific state

---

## Example 4: Optimized API Calls

### Before (Hardcoded URL)
```typescript
const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/user-info`, {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

### After (Using Helper)
```typescript
import { getApiUrl, createFetchOptions } from '@/lib/api-config';
import Cookies from 'js-cookie';

const token = Cookies.get('auth_token');
const response = await fetch(
  `${getApiUrl()}/user-info`,
  createFetchOptions(token, { cache: 'no-store' })
);
```

**Benefits**:
- ✅ Centralized API configuration
- ✅ Automatic error handling
- ✅ Consistent headers
- ✅ Proper cache control

---

## Example 5: Error Handling

### Before (No Error Handling)
```typescript
const data = await fetch(url).then(res => res.json());
```

### After (Proper Error Handling)
```typescript
import { apiFetch } from '@/lib/api-config';

try {
  const data = await apiFetch<ExamData>('/exams/123');
  setExam(data);
} catch (error) {
  console.error('Failed to load exam:', error);
  setError('Không thể tải bài thi. Vui lòng thử lại.');
}
```

**Benefits**:
- ✅ Type-safe API calls
- ✅ Automatic error logging
- ✅ User-friendly error messages
- ✅ Consistent error handling

---

## Caching Decision Tree

```
Is the data user-specific?
├─ YES → Use client-side fetching with cache: 'no-store'
│         Example: User dashboard, exam taking
│
└─ NO → Is the data frequently updated?
    ├─ YES → Use ISR with short revalidate (60s)
    │         Example: Exam list, resources
    │
    └─ NO → Use static generation with long revalidate (3600s)
              Example: Landing page, about page
```

---

## Migration Checklist

### For Each Page:

- [ ] Remove `generateStaticParams()` if not needed
- [ ] Add appropriate caching strategy:
  - [ ] `export const revalidate = X` for ISR
  - [ ] `export const dynamic = 'force-dynamic'` for SSR
- [ ] Replace hardcoded API URLs with `getApiUrl()`
- [ ] Add proper error handling
- [ ] Add loading states
- [ ] Test with and without authentication
- [ ] Verify environment variables work

### For API Calls:

- [ ] Use `createFetchOptions()` for consistent headers
- [ ] Add `cache: 'no-store'` for user-specific data
- [ ] Add `next: { revalidate: X }` for ISR
- [ ] Handle errors gracefully
- [ ] Add TypeScript types
- [ ] Test error scenarios

---

## Testing Locally

### 1. Test Static Pages
```bash
npm run build
npm run start
# Visit http://localhost:3000
```

### 2. Test ISR
```bash
# Make a change to data
# Wait for revalidation period
# Refresh page to see update
```

### 3. Test Dynamic Routes
```bash
# Visit /dashboard/bai-thi/123
# Verify data is always fresh
```

### 4. Test Environment Variables
```bash
# Create .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

---

## Performance Metrics

### Before (S3 Static Export)
- Build time: 2-3 minutes
- Deploy time: 1-2 minutes
- Page load: 500ms (static)
- Cost: $1-2/month

### After (Amplify SSR)
- Build time: 5-7 minutes
- Deploy time: 2-3 minutes
- Page load: 
  - Static: 500ms
  - ISR: 800ms (first request), 500ms (cached)
  - SSR: 1200ms
- Cost: $4-5/month

### Optimization Tips

1. **Minimize SSR pages** - Use ISR when possible
2. **Increase revalidate times** - Balance freshness vs cost
3. **Use static for marketing** - Landing, about, contact pages
4. **Cache API responses** - Reduce backend load
5. **Optimize images** - Use Next.js Image component
