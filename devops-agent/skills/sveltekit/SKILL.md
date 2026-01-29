# SvelteKit Skill

> Read this before creating SvelteKit components, pages, or API routes.

## Page Structure

### Standard Page with Data Loading

```typescript
// +page.server.ts
import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: PageServerLoad = async ({ locals, params }) => {
    const { supabase, session } = locals;
    
    if (!session) {
        throw error(401, 'Unauthorized');
    }
    
    const { data, error: dbError } = await supabase
        .from('platforms')
        .select('*')
        .eq('tenant_id', session.user.tenant_id)
        .order('created_at', { ascending: false });
    
    if (dbError) {
        console.error('Database error:', dbError);
        throw error(500, 'Failed to load platforms');
    }
    
    return { platforms: data ?? [] };
};
```

```svelte
<!-- +page.svelte -->
<script lang="ts">
    import type { PageData } from './$types';
    import { DataTable } from '$lib/components';
    
    export let data: PageData;
</script>

<svelte:head>
    <title>Platforms | FlowMetrics</title>
</svelte:head>

<div class="container mx-auto py-8">
    <h1 class="text-2xl font-bold mb-6">Platforms</h1>
    
    {#if data.platforms.length === 0}
        <p class="text-gray-500">No platforms configured yet.</p>
    {:else}
        <DataTable data={data.platforms} />
    {/if}
</div>
```

## Form Handling with Superforms

```typescript
// +page.server.ts
import { superValidate, fail, message } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import { redirect } from '@sveltejs/kit';

const createPlatformSchema = z.object({
    name: z.string().min(1, 'Name is required').max(100),
    code: z.string()
        .min(3, 'Code must be at least 3 characters')
        .max(10, 'Code must be at most 10 characters')
        .regex(/^[A-Z0-9]+$/, 'Code must be uppercase alphanumeric'),
    description: z.string().optional()
});

export const load = async () => {
    const form = await superValidate(zod(createPlatformSchema));
    return { form };
};

export const actions = {
    default: async ({ request, locals }) => {
        const form = await superValidate(request, zod(createPlatformSchema));
        
        if (!form.valid) {
            return fail(400, { form });
        }
        
        const { supabase, session } = locals;
        
        const { error: dbError } = await supabase
            .from('platforms')
            .insert({
                ...form.data,
                tenant_id: session.user.tenant_id
            });
        
        if (dbError) {
            if (dbError.code === '23505') {
                return message(form, 'A platform with this code already exists', {
                    status: 400
                });
            }
            return message(form, 'Failed to create platform', { status: 500 });
        }
        
        throw redirect(303, '/platforms');
    }
};
```

```svelte
<!-- +page.svelte -->
<script lang="ts">
    import { superForm } from 'sveltekit-superforms';
    import type { PageData } from './$types';
    
    export let data: PageData;
    
    const { form, errors, enhance, submitting, message } = superForm(data.form);
</script>

<form method="POST" use:enhance class="space-y-4 max-w-md">
    {#if $message}
        <div class="alert alert-error">{$message}</div>
    {/if}
    
    <div>
        <label for="name" class="block text-sm font-medium">Name</label>
        <input
            type="text"
            id="name"
            name="name"
            bind:value={$form.name}
            class="input input-bordered w-full"
            class:input-error={$errors.name}
        />
        {#if $errors.name}
            <p class="text-error text-sm mt-1">{$errors.name}</p>
        {/if}
    </div>
    
    <div>
        <label for="code" class="block text-sm font-medium">Code</label>
        <input
            type="text"
            id="code"
            name="code"
            bind:value={$form.code}
            class="input input-bordered w-full uppercase"
            class:input-error={$errors.code}
        />
        {#if $errors.code}
            <p class="text-error text-sm mt-1">{$errors.code}</p>
        {/if}
    </div>
    
    <button type="submit" class="btn btn-primary" disabled={$submitting}>
        {#if $submitting}
            <span class="loading loading-spinner"></span>
        {/if}
        Create Platform
    </button>
</form>
```

## API Routes

```typescript
// src/routes/api/platforms/+server.ts
import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ locals, url }) => {
    const { supabase, session } = locals;
    
    if (!session) {
        throw error(401, { message: 'Unauthorized' });
    }
    
    // Pagination
    const page = parseInt(url.searchParams.get('page') ?? '1');
    const limit = Math.min(parseInt(url.searchParams.get('limit') ?? '20'), 100);
    const offset = (page - 1) * limit;
    
    const { data, error: dbError, count } = await supabase
        .from('platforms')
        .select('*', { count: 'exact' })
        .eq('tenant_id', session.user.tenant_id)
        .range(offset, offset + limit - 1)
        .order('created_at', { ascending: false });
    
    if (dbError) {
        throw error(500, { message: 'Database error' });
    }
    
    return json({
        data,
        meta: {
            page,
            limit,
            total: count ?? 0,
            totalPages: Math.ceil((count ?? 0) / limit)
        }
    });
};

export const POST: RequestHandler = async ({ request, locals }) => {
    const { supabase, session } = locals;
    
    if (!session) {
        throw error(401, { message: 'Unauthorized' });
    }
    
    const body = await request.json();
    
    // Validate with Zod
    const result = createPlatformSchema.safeParse(body);
    if (!result.success) {
        throw error(400, {
            message: 'Validation error',
            errors: result.error.flatten().fieldErrors
        });
    }
    
    const { data, error: dbError } = await supabase
        .from('platforms')
        .insert({
            ...result.data,
            tenant_id: session.user.tenant_id
        })
        .select()
        .single();
    
    if (dbError) {
        throw error(500, { message: dbError.message });
    }
    
    return json({ data }, { status: 201 });
};
```

## Component Patterns

### Data Table Component

```svelte
<!-- src/lib/components/DataTable.svelte -->
<script lang="ts" generics="T extends Record<string, unknown>">
    import { createEventDispatcher } from 'svelte';
    
    export let data: T[];
    export let columns: {
        key: keyof T;
        label: string;
        render?: (value: T[keyof T], row: T) => string;
    }[];
    export let sortable = true;
    
    const dispatch = createEventDispatcher<{
        rowClick: T;
        sort: { key: keyof T; direction: 'asc' | 'desc' };
    }>();
    
    let sortKey: keyof T | null = null;
    let sortDirection: 'asc' | 'desc' = 'asc';
    
    function handleSort(key: keyof T) {
        if (!sortable) return;
        
        if (sortKey === key) {
            sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            sortKey = key;
            sortDirection = 'asc';
        }
        
        dispatch('sort', { key, direction: sortDirection });
    }
</script>

<div class="overflow-x-auto">
    <table class="table table-zebra w-full">
        <thead>
            <tr>
                {#each columns as column}
                    <th
                        class:cursor-pointer={sortable}
                        on:click={() => handleSort(column.key)}
                    >
                        {column.label}
                        {#if sortKey === column.key}
                            <span>{sortDirection === 'asc' ? '↑' : '↓'}</span>
                        {/if}
                    </th>
                {/each}
            </tr>
        </thead>
        <tbody>
            {#each data as row}
                <tr
                    class="hover cursor-pointer"
                    on:click={() => dispatch('rowClick', row)}
                >
                    {#each columns as column}
                        <td>
                            {#if column.render}
                                {@html column.render(row[column.key], row)}
                            {:else}
                                {row[column.key]}
                            {/if}
                        </td>
                    {/each}
                </tr>
            {/each}
        </tbody>
    </table>
</div>
```

### Modal Component

```svelte
<!-- src/lib/components/Modal.svelte -->
<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    import { fade, scale } from 'svelte/transition';
    
    export let open = false;
    export let title = '';
    export let size: 'sm' | 'md' | 'lg' = 'md';
    
    const dispatch = createEventDispatcher<{ close: void }>();
    
    const sizeClasses = {
        sm: 'max-w-sm',
        md: 'max-w-md',
        lg: 'max-w-2xl'
    };
    
    function handleKeydown(e: KeyboardEvent) {
        if (e.key === 'Escape') {
            dispatch('close');
        }
    }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if open}
    <div
        class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
        transition:fade={{ duration: 150 }}
        on:click|self={() => dispatch('close')}
    >
        <div
            class="bg-base-100 rounded-lg shadow-xl w-full {sizeClasses[size]}"
            transition:scale={{ duration: 150, start: 0.95 }}
        >
            <div class="flex items-center justify-between p-4 border-b">
                <h3 class="text-lg font-semibold">{title}</h3>
                <button
                    class="btn btn-ghost btn-sm btn-circle"
                    on:click={() => dispatch('close')}
                >
                    ✕
                </button>
            </div>
            
            <div class="p-4">
                <slot />
            </div>
            
            {#if $$slots.footer}
                <div class="flex justify-end gap-2 p-4 border-t">
                    <slot name="footer" />
                </div>
            {/if}
        </div>
    </div>
{/if}
```

## Hooks

### Authentication Hook

```typescript
// src/hooks.server.ts
import { createServerClient } from '@supabase/ssr';
import type { Handle } from '@sveltejs/kit';
import { sequence } from '@sveltejs/kit/hooks';

const supabase: Handle = async ({ event, resolve }) => {
    event.locals.supabase = createServerClient(
        env.PUBLIC_SUPABASE_URL,
        env.PUBLIC_SUPABASE_ANON_KEY,
        {
            cookies: {
                get: (key) => event.cookies.get(key),
                set: (key, value, options) => {
                    event.cookies.set(key, value, options);
                },
                remove: (key, options) => {
                    event.cookies.delete(key, options);
                }
            }
        }
    );

    event.locals.getSession = async () => {
        const {
            data: { session }
        } = await event.locals.supabase.auth.getSession();
        return session;
    };

    return resolve(event, {
        filterSerializedResponseHeaders(name) {
            return name === 'content-range';
        }
    });
};

const auth: Handle = async ({ event, resolve }) => {
    event.locals.session = await event.locals.getSession();
    return resolve(event);
};

export const handle = sequence(supabase, auth);
```

## Error Handling

```svelte
<!-- src/routes/+error.svelte -->
<script lang="ts">
    import { page } from '$app/stores';
</script>

<div class="min-h-screen flex items-center justify-center">
    <div class="text-center">
        <h1 class="text-6xl font-bold text-error">{$page.status}</h1>
        <p class="text-xl mt-4">{$page.error?.message ?? 'Something went wrong'}</p>
        <a href="/" class="btn btn-primary mt-8">Go Home</a>
    </div>
</div>
```

## Testing

```typescript
// src/lib/utils/formatCurrency.test.ts
import { describe, it, expect } from 'vitest';
import { formatCurrency } from './formatCurrency';

describe('formatCurrency', () => {
    it('formats positive numbers', () => {
        expect(formatCurrency(1234.56)).toBe('$1,234.56');
    });
    
    it('formats negative numbers', () => {
        expect(formatCurrency(-1234.56)).toBe('-$1,234.56');
    });
    
    it('handles zero', () => {
        expect(formatCurrency(0)).toBe('$0.00');
    });
});
```
