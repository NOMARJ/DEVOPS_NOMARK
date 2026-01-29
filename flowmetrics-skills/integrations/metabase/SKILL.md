# Metabase Integration

> Embed analytics dashboards and run queries against self-hosted Metabase.

## When to Use

- Embedding dashboards in client/admin portals
- Running ad-hoc analytics queries
- Generating data for reports
- Scheduling automated data exports

## Prerequisites

- Self-hosted Metabase instance
- METABASE_URL environment variable
- METABASE_USERNAME and METABASE_PASSWORD (or API key)
- METABASE_SECRET_KEY for signed embeds

## Authentication

### Session-based (for API calls)
```python
import httpx

async def get_session():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{METABASE_URL}/api/session",
            json={"username": USERNAME, "password": PASSWORD}
        )
        return resp.json()["id"]

# Use session token in headers
headers = {"X-Metabase-Session": session_token}
```

### Signed Embeds (for iframes)
```python
import jwt
import time

def generate_embed_url(resource_type, resource_id, params=None):
    payload = {
        "resource": {resource_type: resource_id},
        "params": params or {},
        "exp": int(time.time()) + 3600,  # 1 hour
    }
    
    token = jwt.encode(payload, METABASE_SECRET_KEY, algorithm="HS256")
    return f"{METABASE_URL}/embed/{resource_type}/{token}"
```

## Embedding Dashboards

### SvelteKit Component

```svelte
<script lang="ts">
    export let dashboardId: number;
    export let params: Record<string, string> = {};
    
    let embedUrl: string;
    
    onMount(async () => {
        const response = await fetch('/api/metabase/embed-url', {
            method: 'POST',
            body: JSON.stringify({
                type: 'dashboard',
                id: dashboardId,
                params
            })
        });
        const data = await response.json();
        embedUrl = data.url;
    });
</script>

{#if embedUrl}
    <iframe
        src={embedUrl}
        frameborder="0"
        width="100%"
        height="600"
        allowtransparency
    />
{:else}
    <div class="loading">Loading dashboard...</div>
{/if}
```

### Server Endpoint

```typescript
// src/routes/api/metabase/embed-url/+server.ts
import { json } from '@sveltejs/kit';
import jwt from 'jsonwebtoken';

export async function POST({ request }) {
    const { type, id, params } = await request.json();
    
    const payload = {
        resource: { [type]: id },
        params: params || {},
        exp: Math.floor(Date.now() / 1000) + 3600,
    };
    
    const token = jwt.sign(payload, METABASE_SECRET_KEY);
    const url = `${METABASE_URL}/embed/${type}/${token}`;
    
    return json({ url });
}
```

## Running Queries

### Saved Questions
```python
async def run_question(question_id: int, params: dict = None):
    token = await get_session()
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{METABASE_URL}/api/card/{question_id}/query",
            headers={"X-Metabase-Session": token},
            json={"parameters": params or {}}
        )
        data = resp.json()
    
    return {
        "columns": [c["name"] for c in data["data"]["cols"]],
        "rows": data["data"]["rows"],
    }
```

### Ad-hoc SQL
```python
async def run_sql(database_id: int, query: str):
    token = await get_session()
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{METABASE_URL}/api/dataset",
            headers={"X-Metabase-Session": token},
            json={
                "database": database_id,
                "native": {"query": query},
                "type": "native",
            }
        )
        return resp.json()
```

## Dashboard Organization

### FlowMetrics Dashboard Structure

```
Collections/
├── FlowMetrics Internal/
│   ├── Operations Dashboards/
│   │   ├── Daily Ingestion Status
│   │   ├── Data Quality Overview
│   │   └── Platform Health
│   └── Development/
│       └── Query Sandbox
│
└── Client Dashboards/
    ├── [Client A]/
    │   ├── Monthly Flows
    │   ├── Platform Breakdown
    │   └── Trend Analysis
    └── [Client B]/
        └── ...
```

### Dashboard Parameters

Lock parameters for client isolation:

```python
# Generate embed with locked client filter
embed_url = generate_embed_url(
    "dashboard",
    42,
    params={"client_id": "abc123"}  # Locked - user can't change
)
```

## Scheduled Reports (Pulses)

### Create Pulse via API
```python
async def create_pulse(name: str, cards: list, schedule: dict, channels: list):
    token = await get_session()
    
    pulse = {
        "name": name,
        "cards": [{"id": c, "include_csv": True} for c in cards],
        "channels": channels,
        "skip_if_empty": True,
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{METABASE_URL}/api/pulse",
            headers={"X-Metabase-Session": token},
            json=pulse
        )
        return resp.json()
```

### Channel Types
```python
# Email
{"channel_type": "email", "recipients": [{"email": "user@example.com"}]}

# Slack
{"channel_type": "slack", "channel": "#analytics"}
```

## n8n Integration

### Fetch Dashboard Data
```json
{
  "name": "Get Metabase Data",
  "type": "n8n-nodes-base.httpRequest",
  "parameters": {
    "method": "POST",
    "url": "={{$env.METABASE_URL}}/api/card/{{$json.question_id}}/query",
    "headers": {
      "X-Metabase-Session": "={{$env.METABASE_SESSION}}"
    },
    "body": {
      "parameters": "={{$json.params}}"
    }
  }
}
```

### Trigger Report Generation
```json
{
  "name": "Trigger Metabase Export",
  "type": "n8n-nodes-base.httpRequest",
  "parameters": {
    "method": "POST",
    "url": "={{$env.METABASE_URL}}/api/card/{{$json.question_id}}/query/csv",
    "headers": {
      "X-Metabase-Session": "={{$env.METABASE_SESSION}}"
    }
  }
}
```

## Embedding Best Practices

1. **Use signed embeds**: Never expose session tokens to clients
2. **Lock sensitive params**: Always lock client_id, tenant_id
3. **Set expiry**: Short-lived tokens (1 hour max)
4. **Cache tokens**: Don't generate for every request
5. **Monitor usage**: Track embed views for billing

## Styling Embeds

### Hide Metabase Chrome
Add hash parameters to embed URL:

```
?bordered=false    # Remove border
&titled=false      # Remove title
&theme=transparent # Transparent background
```

### Custom CSS
```css
/* In your portal CSS */
iframe[src*="metabase"] {
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
```

## Troubleshooting

### "Embedding not enabled"
- Enable embedding in Admin > Settings > Embedding
- Set the secret key

### "Invalid token"
- Check METABASE_SECRET_KEY matches admin setting
- Verify token hasn't expired
- Check for URL encoding issues

### Slow dashboard loads
- Add filters to reduce data volume
- Enable caching in Metabase settings
- Consider materialized views for heavy queries

## Security Considerations

1. **Never expose service credentials** to frontend
2. **Use signed embeds** for all client-facing dashboards
3. **Lock parameters** to prevent data leakage
4. **Audit access** via Metabase audit logs
5. **Rotate secret key** periodically
