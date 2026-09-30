---
name: nextjs-app-router-patterns
description: Build Next.js 13+ App Router applications with server components, client components, API routes, middleware, and streaming. Use when implementing Next.js features, route handlers, or RSC patterns.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
---

# Next.js App Router Patterns

## Page Structure

```typescript
// app/dashboard/page.tsx
export default async function DashboardPage() {
  const data = await fetch('https://api.example.com/data')
  return <div>{/* Server Component */}</div>
}
```

## Server vs Client Components

**Server Component (default):**
```typescript
// No "use client" = Server Component
export default async function ServerComp() {
  const data = await fetchData() // Direct async/await
  return <div>{data}</div>
}
```

**Client Component:**
```typescript
'use client'
import { useState } from 'react'

export default function ClientComp() {
  const [count, setCount] = useState(0)
  return <button onClick={() => setCount(count + 1)}>{count}</button>
}
```

## API Routes

```typescript
// app/api<REDACTED_USERPATH>
import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  const users = await db.user.findMany()
  return NextResponse.json(users)
}

export async function POST(request: NextRequest) {
  const body = await request.json()
  const user = await db.user.create({ data: body })
  return NextResponse.json(user, { status: 201 })
}
```

## Layouts

```typescript
// app/dashboard/layout.tsx
export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="dashboard">
      <nav>{/* Sidebar */}</nav>
      <main>{children}</main>
    </div>
  )
}
```

## Loading & Error States

```typescript
// app/dashboard/loading.tsx
export default function Loading() {
  return <div>Loading...</div>
}

// app/dashboard/error.tsx
'use client'
export default function Error({ error, reset }: {
  error: Error
  reset: () => void
}) {
  return <div>Error: {error.message}</div>
}
```

## Data Fetching

```typescript
// Server Component - Direct fetch
async function getData() {
  const res = await fetch('https://api.example.com', {
    cache: 'no-store', // or 'force-cache'
  })
  return res.json()
}

export default async function Page() {
  const data = await getData()
  return <div>{data.title}</div>
}
```

## Middleware

```typescript
// middleware.ts (root level)
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const token = request.cookies.get('token')

  if (!token && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: '/dashboard/:path*',
}
```