---
name: nextjs
description: "NextJS App Router patterns. Read before creating pages, components, or API routes."
---

# NextJS Skill

> Read this before creating NextJS pages, components, or API routes.

## Project Structure (App Router)

```
app/
├── layout.tsx              # Root layout
├── page.tsx                # Home page
├── globals.css
├── loading.tsx             # Loading UI
├── error.tsx               # Error boundary
├── not-found.tsx           # 404 page
├── (auth)/                 # Route group (no URL segment)
│   ├── login/page.tsx
│   └── register/page.tsx
├── dashboard/
│   ├── layout.tsx          # Nested layout
│   ├── page.tsx
│   └── [id]/               # Dynamic route
│       └── page.tsx
├── api/
│   └── tasks/
│       └── route.ts        # API route
components/
├── ui/                     # Reusable UI components
├── forms/                  # Form components
└── layouts/                # Layout components
lib/
├── db.ts                   # Database client
├── auth.ts                 # Auth utilities
└── utils.ts                # Helper functions
types/
└── index.ts                # TypeScript types
```

## Server vs Client Components

### Server Components (Default)

```tsx
// app/tasks/page.tsx
// Server Component - can fetch data directly
import { db } from '@/lib/db';
import { TaskList } from '@/components/TaskList';

export default async function TasksPage() {
    const tasks = await db.task.findMany({
        orderBy: { createdAt: 'desc' }
    });

    return (
        <main className="container mx-auto py-8">
            <h1 className="text-2xl font-bold mb-6">Tasks</h1>
            <TaskList tasks={tasks} />
        </main>
    );
}
```

### Client Components

```tsx
// components/TaskList.tsx
'use client';

import { useState } from 'react';
import type { Task } from '@/types';

interface TaskListProps {
    tasks: Task[];
}

export function TaskList({ tasks: initialTasks }: TaskListProps) {
    const [tasks, setTasks] = useState(initialTasks);
    const [filter, setFilter] = useState<'all' | 'active' | 'completed'>('all');

    const filteredTasks = tasks.filter(task => {
        if (filter === 'active') return !task.completed;
        if (filter === 'completed') return task.completed;
        return true;
    });

    return (
        <div>
            <div className="flex gap-2 mb-4">
                {(['all', 'active', 'completed'] as const).map((f) => (
                    <button
                        key={f}
                        onClick={() => setFilter(f)}
                        className={`px-3 py-1 rounded ${
                            filter === f ? 'bg-blue-500 text-white' : 'bg-gray-200'
                        }`}
                    >
                        {f.charAt(0).toUpperCase() + f.slice(1)}
                    </button>
                ))}
            </div>

            <ul className="space-y-2">
                {filteredTasks.map(task => (
                    <li key={task.id} className="p-4 bg-white rounded shadow">
                        {task.title}
                    </li>
                ))}
            </ul>
        </div>
    );
}
```

## Data Fetching

### Server-Side Fetching

```tsx
// app/tasks/page.tsx
async function getTasks() {
    const res = await fetch('https://api.example.com/tasks', {
        next: { revalidate: 60 } // Revalidate every 60 seconds
    });

    if (!res.ok) {
        throw new Error('Failed to fetch tasks');
    }

    return res.json();
}

export default async function TasksPage() {
    const tasks = await getTasks();
    return <TaskList tasks={tasks} />;
}
```

### With Database (Prisma)

```tsx
// app/tasks/page.tsx
import { prisma } from '@/lib/db';

export default async function TasksPage() {
    const tasks = await prisma.task.findMany({
        where: { userId: 'user-id' },
        include: { subtasks: true },
        orderBy: { createdAt: 'desc' }
    });

    return <TaskList tasks={tasks} />;
}
```

## Server Actions

### Form Handling

```tsx
// app/tasks/actions.ts
'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { z } from 'zod';
import { prisma } from '@/lib/db';

const createTaskSchema = z.object({
    title: z.string().min(1, 'Title is required').max(200),
    priority: z.enum(['low', 'medium', 'high']).default('medium'),
    dueDate: z.string().optional()
});

export async function createTask(formData: FormData) {
    const rawData = {
        title: formData.get('title'),
        priority: formData.get('priority'),
        dueDate: formData.get('dueDate')
    };

    const result = createTaskSchema.safeParse(rawData);

    if (!result.success) {
        return {
            error: result.error.flatten().fieldErrors
        };
    }

    await prisma.task.create({
        data: {
            title: result.data.title,
            priority: result.data.priority,
            dueDate: result.data.dueDate ? new Date(result.data.dueDate) : null
        }
    });

    revalidatePath('/tasks');
    redirect('/tasks');
}

export async function deleteTask(id: string) {
    await prisma.task.delete({ where: { id } });
    revalidatePath('/tasks');
}
```

### Using in Forms

```tsx
// app/tasks/new/page.tsx
import { createTask } from '../actions';

export default function NewTaskPage() {
    return (
        <form action={createTask} className="space-y-4 max-w-md">
            <div>
                <label htmlFor="title" className="block text-sm font-medium">
                    Title
                </label>
                <input
                    type="text"
                    id="title"
                    name="title"
                    required
                    className="mt-1 block w-full rounded border-gray-300 shadow-sm"
                />
            </div>

            <div>
                <label htmlFor="priority" className="block text-sm font-medium">
                    Priority
                </label>
                <select
                    id="priority"
                    name="priority"
                    className="mt-1 block w-full rounded border-gray-300 shadow-sm"
                >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                </select>
            </div>

            <button
                type="submit"
                className="w-full bg-blue-500 text-white py-2 rounded hover:bg-blue-600"
            >
                Create Task
            </button>
        </form>
    );
}
```

### Client-Side with useFormState

```tsx
'use client';

import { useFormState, useFormStatus } from 'react-dom';
import { createTask } from '../actions';

function SubmitButton() {
    const { pending } = useFormStatus();

    return (
        <button
            type="submit"
            disabled={pending}
            className="w-full bg-blue-500 text-white py-2 rounded disabled:opacity-50"
        >
            {pending ? 'Creating...' : 'Create Task'}
        </button>
    );
}

export function TaskForm() {
    const [state, formAction] = useFormState(createTask, null);

    return (
        <form action={formAction} className="space-y-4">
            <div>
                <input
                    type="text"
                    name="title"
                    placeholder="Task title"
                    className="w-full rounded border p-2"
                />
                {state?.error?.title && (
                    <p className="text-red-500 text-sm mt-1">{state.error.title}</p>
                )}
            </div>

            <SubmitButton />
        </form>
    );
}
```

## API Routes

### Route Handlers

```ts
// app/api/tasks/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/db';
import { z } from 'zod';

export async function GET(request: NextRequest) {
    const searchParams = request.nextUrl.searchParams;
    const page = parseInt(searchParams.get('page') ?? '1');
    const limit = Math.min(parseInt(searchParams.get('limit') ?? '20'), 100);

    const [tasks, total] = await Promise.all([
        prisma.task.findMany({
            skip: (page - 1) * limit,
            take: limit,
            orderBy: { createdAt: 'desc' }
        }),
        prisma.task.count()
    ]);

    return NextResponse.json({
        data: tasks,
        meta: {
            page,
            limit,
            total,
            totalPages: Math.ceil(total / limit)
        }
    });
}

const createTaskSchema = z.object({
    title: z.string().min(1).max(200),
    priority: z.enum(['low', 'medium', 'high']).optional()
});

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();
        const result = createTaskSchema.safeParse(body);

        if (!result.success) {
            return NextResponse.json(
                { error: result.error.flatten().fieldErrors },
                { status: 400 }
            );
        }

        const task = await prisma.task.create({
            data: result.data
        });

        return NextResponse.json({ data: task }, { status: 201 });
    } catch (error) {
        return NextResponse.json(
            { error: 'Internal server error' },
            { status: 500 }
        );
    }
}
```

### Dynamic Route Handlers

```ts
// app/api/tasks/[id]/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/db';

interface RouteParams {
    params: { id: string };
}

export async function GET(request: NextRequest, { params }: RouteParams) {
    const task = await prisma.task.findUnique({
        where: { id: params.id }
    });

    if (!task) {
        return NextResponse.json(
            { error: 'Task not found' },
            { status: 404 }
        );
    }

    return NextResponse.json({ data: task });
}

export async function PATCH(request: NextRequest, { params }: RouteParams) {
    const body = await request.json();

    const task = await prisma.task.update({
        where: { id: params.id },
        data: body
    });

    return NextResponse.json({ data: task });
}

export async function DELETE(request: NextRequest, { params }: RouteParams) {
    await prisma.task.delete({
        where: { id: params.id }
    });

    return new NextResponse(null, { status: 204 });
}
```

## Layouts & Templates

### Root Layout

```tsx
// app/layout.tsx
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
    title: 'My App',
    description: 'App description'
};

export default function RootLayout({
    children
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en">
            <body className={inter.className}>
                <nav className="border-b p-4">
                    {/* Navigation */}
                </nav>
                <main>{children}</main>
            </body>
        </html>
    );
}
```

### Loading & Error States

```tsx
// app/tasks/loading.tsx
export default function Loading() {
    return (
        <div className="flex items-center justify-center min-h-screen">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
        </div>
    );
}

// app/tasks/error.tsx
'use client';

export default function Error({
    error,
    reset
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    return (
        <div className="flex flex-col items-center justify-center min-h-screen">
            <h2 className="text-xl font-bold mb-4">Something went wrong!</h2>
            <p className="text-gray-600 mb-4">{error.message}</p>
            <button
                onClick={reset}
                className="px-4 py-2 bg-blue-500 text-white rounded"
            >
                Try again
            </button>
        </div>
    );
}
```

## Authentication (NextAuth.js)

```ts
// lib/auth.ts
import NextAuth from 'next-auth';
import GitHub from 'next-auth/providers/github';

export const { handlers, auth, signIn, signOut } = NextAuth({
    providers: [GitHub],
    callbacks: {
        async session({ session, token }) {
            if (token.sub) {
                session.user.id = token.sub;
            }
            return session;
        }
    }
});

// app/api/auth/[...nextauth]/route.ts
import { handlers } from '@/lib/auth';
export const { GET, POST } = handlers;
```

### Protected Routes

```tsx
// middleware.ts
import { auth } from '@/lib/auth';

export default auth((req) => {
    if (!req.auth && req.nextUrl.pathname !== '/login') {
        const loginUrl = new URL('/login', req.nextUrl.origin);
        loginUrl.searchParams.set('callbackUrl', req.nextUrl.pathname);
        return Response.redirect(loginUrl);
    }
});

export const config = {
    matcher: ['/dashboard/:path*', '/settings/:path*']
};
```

## Testing

### Component Tests (Jest + React Testing Library)

```tsx
// __tests__/TaskList.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { TaskList } from '@/components/TaskList';

const mockTasks = [
    { id: '1', title: 'Task 1', completed: false },
    { id: '2', title: 'Task 2', completed: true }
];

describe('TaskList', () => {
    it('renders all tasks', () => {
        render(<TaskList tasks={mockTasks} />);

        expect(screen.getByText('Task 1')).toBeInTheDocument();
        expect(screen.getByText('Task 2')).toBeInTheDocument();
    });

    it('filters active tasks', () => {
        render(<TaskList tasks={mockTasks} />);

        fireEvent.click(screen.getByText('Active'));

        expect(screen.getByText('Task 1')).toBeInTheDocument();
        expect(screen.queryByText('Task 2')).not.toBeInTheDocument();
    });
});
```

### E2E Tests (Playwright)

```ts
// e2e/tasks.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Tasks', () => {
    test('can create a new task', async ({ page }) => {
        await page.goto('/tasks/new');

        await page.fill('[name="title"]', 'New Task');
        await page.selectOption('[name="priority"]', 'high');
        await page.click('button[type="submit"]');

        await expect(page).toHaveURL('/tasks');
        await expect(page.getByText('New Task')).toBeVisible();
    });
});
```

## Common Gotchas

1. **'use client' placement** - Must be at top of file, before imports
2. **Server/Client boundary** - Can't import server-only code in client components
3. **Caching** - `fetch()` caches by default, use `{ cache: 'no-store' }` for dynamic data
4. **Revalidation** - Use `revalidatePath()` or `revalidateTag()` after mutations
5. **Params in App Router** - Dynamic params are promises in async components

## Useful Commands

```bash
# Development
npm run dev

# Build
npm run build

# Start production
npm start

# Type check
npx tsc --noEmit

# Lint
npm run lint

# Test
npm test

# E2E tests
npx playwright test
```

## Environment Variables

```env
# .env.local (not committed)
DATABASE_URL="postgresql://..."
NEXTAUTH_SECRET="..."
NEXTAUTH_URL="http://localhost:3000"

# .env (defaults, can be committed)
NEXT_PUBLIC_APP_URL="https://example.com"
```

Access in code:
- Server: `process.env.DATABASE_URL`
- Client: `process.env.NEXT_PUBLIC_APP_URL` (must have `NEXT_PUBLIC_` prefix)
