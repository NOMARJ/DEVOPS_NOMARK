# n8n Workflow Skill

> Read this before creating or modifying n8n workflows.

## Workflow Structure

```json
{
  "name": "Descriptive Workflow Name",
  "nodes": [...],
  "connections": {...},
  "settings": {
    "executionOrder": "v1"
  },
  "staticData": null,
  "tags": [{ "name": "category" }]
}
```

## Common Node Patterns

### Webhook Trigger

```json
{
  "parameters": {
    "httpMethod": "POST",
    "path": "your-webhook-path",
    "options": {
      "responseMode": "lastNode"
    }
  },
  "id": "webhook-trigger",
  "name": "Webhook",
  "type": "n8n-nodes-base.webhook",
  "typeVersion": 2,
  "position": [240, 300],
  "webhookId": "unique-webhook-id"
}
```

### PostgreSQL Query

```json
{
  "parameters": {
    "operation": "select",
    "schema": { "__rl": true, "mode": "list", "value": "public" },
    "table": { "__rl": true, "mode": "list", "value": "your_table" },
    "limit": 50,
    "where": {
      "values": [
        { "column": "status", "operator": "equal", "value": "={{ $json.status }}" }
      ]
    },
    "sort": {
      "values": [
        { "column": "created_at", "direction": "DESC" }
      ]
    }
  },
  "id": "postgres-query",
  "name": "Get Records",
  "type": "n8n-nodes-base.postgres",
  "typeVersion": 2.5,
  "position": [460, 300],
  "credentials": { "postgres": { "id": "cred-id", "name": "Production DB" } }
}
```

### HTTP Request

```json
{
  "parameters": {
    "method": "POST",
    "url": "https://api.example.com/endpoint",
    "authentication": "predefinedCredentialType",
    "nodeCredentialType": "httpHeaderAuth",
    "sendBody": true,
    "specifyBody": "json",
    "jsonBody": "={{ JSON.stringify({ data: $json.data }) }}",
    "options": {
      "timeout": 30000,
      "response": {
        "response": {
          "responseFormat": "json"
        }
      }
    }
  },
  "id": "http-request",
  "name": "Call API",
  "type": "n8n-nodes-base.httpRequest",
  "typeVersion": 4.2,
  "position": [680, 300],
  "credentials": { "httpHeaderAuth": { "id": "cred-id", "name": "API Key" } }
}
```

### Code Node (JavaScript)

```json
{
  "parameters": {
    "jsCode": "// Process input data\nconst items = $input.all();\n\nconst results = items.map(item => {\n  const data = item.json;\n  \n  return {\n    json: {\n      ...data,\n      processed: true,\n      timestamp: new Date().toISOString()\n    }\n  };\n});\n\nreturn results;"
  },
  "id": "code-process",
  "name": "Process Data",
  "type": "n8n-nodes-base.code",
  "typeVersion": 2,
  "position": [900, 300]
}
```

### IF Condition

```json
{
  "parameters": {
    "conditions": {
      "options": {
        "caseSensitive": true,
        "leftValue": "",
        "typeValidation": "strict"
      },
      "conditions": [
        {
          "leftValue": "={{ $json.status }}",
          "rightValue": "success",
          "operator": {
            "type": "string",
            "operation": "equals"
          }
        }
      ]
    }
  },
  "id": "if-condition",
  "name": "Check Status",
  "type": "n8n-nodes-base.if",
  "typeVersion": 2,
  "position": [1120, 300]
}
```

### Switch (Router)

```json
{
  "parameters": {
    "rules": {
      "rules": [
        {
          "outputKey": "create",
          "conditions": {
            "conditions": [
              {
                "leftValue": "={{ $json.action }}",
                "rightValue": "create",
                "operator": { "type": "string", "operation": "equals" }
              }
            ]
          }
        },
        {
          "outputKey": "update",
          "conditions": {
            "conditions": [
              {
                "leftValue": "={{ $json.action }}",
                "rightValue": "update",
                "operator": { "type": "string", "operation": "equals" }
              }
            ]
          }
        },
        {
          "outputKey": "delete",
          "conditions": {
            "conditions": [
              {
                "leftValue": "={{ $json.action }}",
                "rightValue": "delete",
                "operator": { "type": "string", "operation": "equals" }
              }
            ]
          }
        }
      ]
    }
  },
  "id": "switch-action",
  "name": "Route by Action",
  "type": "n8n-nodes-base.switch",
  "typeVersion": 3,
  "position": [680, 300]
}
```

### Slack Message

```json
{
  "parameters": {
    "select": "channel",
    "channelId": {
      "__rl": true,
      "mode": "id",
      "value": "={{ $json.channel_id }}"
    },
    "text": "={{ $json.message }}",
    "blocksUi": "={{ JSON.stringify($json.blocks) }}",
    "otherOptions": {
      "includeLinkToWorkflow": false
    }
  },
  "id": "slack-send",
  "name": "Send Slack Message",
  "type": "n8n-nodes-base.slack",
  "typeVersion": 2.2,
  "position": [1340, 300],
  "credentials": { "slackApi": { "id": "cred-id", "name": "Slack Bot" } }
}
```

### Error Trigger

```json
{
  "parameters": {},
  "id": "error-trigger",
  "name": "Error Trigger",
  "type": "n8n-nodes-base.errorTrigger",
  "typeVersion": 1,
  "position": [240, 500]
}
```

## Connections Format

```json
{
  "connections": {
    "Webhook": {
      "main": [
        [{ "node": "Process Data", "type": "main", "index": 0 }]
      ]
    },
    "Process Data": {
      "main": [
        [{ "node": "Check Status", "type": "main", "index": 0 }]
      ]
    },
    "Check Status": {
      "main": [
        [{ "node": "Success Handler", "type": "main", "index": 0 }],
        [{ "node": "Error Handler", "type": "main", "index": 0 }]
      ]
    }
  }
}
```

## Expression Examples

```javascript
// Access current item
$json.fieldName

// Access specific node output
$('Node Name').item.json.field

// Access all items from node
$('Node Name').all()

// Access first item from node  
$('Node Name').first()

// Access environment variable
$env.VARIABLE_NAME

// Current timestamp
{{ new Date().toISOString() }}

// Conditional
{{ $json.value ? 'Yes' : 'No' }}

// Format date
{{ DateTime.fromISO($json.date).toFormat('yyyy-MM-dd') }}

// Parse JSON string
{{ JSON.parse($json.jsonString) }}

// String operations
{{ $json.name.toLowerCase().trim() }}

// Array operations
{{ $json.items.map(i => i.name).join(', ') }}

// Math
{{ Math.round($json.amount * 100) / 100 }}

// Default value
{{ $json.optional ?? 'default' }}
```

## Error Handling Pattern

```json
{
  "nodes": [
    {
      "parameters": {},
      "id": "error-trigger",
      "name": "On Error",
      "type": "n8n-nodes-base.errorTrigger",
      "typeVersion": 1,
      "position": [240, 500]
    },
    {
      "parameters": {
        "jsCode": "const error = $input.first().json;\n\nreturn [{\n  json: {\n    workflow: error.workflow?.name,\n    node: error.node?.name,\n    message: error.message,\n    timestamp: new Date().toISOString()\n  }\n}];"
      },
      "id": "format-error",
      "name": "Format Error",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [460, 500]
    },
    {
      "parameters": {
        "select": "channel",
        "channelId": { "__rl": true, "value": "C0123456789" },
        "text": ":x: Workflow Error\n\nWorkflow: {{ $json.workflow }}\nNode: {{ $json.node }}\nError: {{ $json.message }}"
      },
      "id": "alert-slack",
      "name": "Alert Slack",
      "type": "n8n-nodes-base.slack",
      "typeVersion": 2.2,
      "position": [680, 500]
    }
  ]
}
```

## Workflow Settings

```json
{
  "settings": {
    "executionOrder": "v1",
    "saveManualExecutions": true,
    "callerPolicy": "workflowsFromSameOwner",
    "errorWorkflow": "error-handler-workflow-id",
    "timezone": "Australia/Sydney",
    "saveExecutionProgress": true
  }
}
```

## Best Practices

1. **Use descriptive node names**: "Get Active Platforms" not "Postgres1"
2. **Add error handling**: Always have an error workflow or error trigger
3. **Use credentials**: Never hardcode API keys or secrets
4. **Comment complex code**: Add comments in Code nodes
5. **Test with static data**: Use "Execute Node" before full runs
6. **Use tags**: Organize workflows by category
7. **Set timeouts**: Configure appropriate timeouts for HTTP requests
8. **Log important events**: Send to Slack or logging service
9. **Use environment variables**: `$env.VARIABLE_NAME` for config
10. **Version control**: Export and commit workflow JSON files

## Slack Block Kit Templates

### Simple Message with Button

```javascript
const blocks = [
  {
    type: "section",
    text: {
      type: "mrkdwn",
      text: `*${title}*\n\n${description}`
    }
  },
  {
    type: "actions",
    elements: [
      {
        type: "button",
        text: { type: "plain_text", text: "Approve" },
        style: "primary",
        action_id: "approve",
        value: JSON.stringify({ id: recordId })
      },
      {
        type: "button", 
        text: { type: "plain_text", text: "Reject" },
        style: "danger",
        action_id: "reject",
        value: JSON.stringify({ id: recordId })
      }
    ]
  }
];
```

### Status Update

```javascript
const blocks = [
  {
    type: "section",
    text: {
      type: "mrkdwn",
      text: `${emoji} *${title}*`
    }
  },
  {
    type: "context",
    elements: [
      {
        type: "mrkdwn",
        text: `Task: \`${taskId}\` | Status: ${status} | <${url}|View Details>`
      }
    ]
  }
];
```

## Testing Workflows

1. **Manual execution**: Click "Execute Workflow"
2. **Test webhook**: Use curl or Postman
3. **Pin data**: Pin test data to nodes for consistent testing
4. **Check executions**: Review execution history for errors
5. **Use "Execute Node"**: Test individual nodes

```bash
# Test webhook
curl -X POST https://n8n.yourdomain.com/webhook/your-path \
  -H "Content-Type: application/json" \
  -d '{"test": true, "data": "example"}'
```
