# Carbone Report Generation

> Generate professional documents from templates using Carbone's JSON-to-document engine.

## When to Use

- Creating reports from data (monthly flows, board packs)
- Generating client-facing documents
- Batch document generation
- Converting JSON data to Word, Excel, PowerPoint, or PDF

## Prerequisites

- Carbone installed (`npm install carbone` or Docker image)
- Template files (`.docx`, `.xlsx`, `.pptx`, `.odt`)
- CARBONE_TEMPLATES_DIR environment variable set

## Template Syntax

Carbone uses curly braces `{d.field}` to inject data:

### Basic Fields
```
{d.client_name}          → Client name from data
{d.period}               → Report period
{d.generated_at:formatD} → Formatted date
```

### Loops (for arrays)
```
{d.platforms[i].name}    → Platform name in loop
{d.platforms[i].code}    → Platform code
{d.platforms[i+1]}       → Moves to next item (ends loop)
```

### Conditionals
```
{d.show_chart:showBegin}
  Chart content here
{d.show_chart:showEnd}

{d.value:ifGT(0)}positive{d.value:else}zero or negative{d.value:endIf}
```

### Formatters
```
{d.amount:formatN(2)}           → Number with 2 decimals
{d.date:formatD(YYYY-MM-DD)}    → Date formatting
{d.value:formatC(AUD)}          → Currency
{d.name:upper}                  → UPPERCASE
{d.name:lower}                  → lowercase
```

## FlowMetrics Report Templates

### Monthly Flows Report
Template: `templates/reports/monthly_flows.docx`

Data structure:
```json
{
  "client_name": "Example Fund",
  "period": "January 2024",
  "total_inflows": 15000000,
  "total_outflows": 8500000,
  "net_flows": 6500000,
  "platforms": [
    {
      "name": "Asgard",
      "inflows": 5000000,
      "outflows": 2000000,
      "net": 3000000
    }
  ],
  "commentary": "Strong month driven by..."
}
```

### Board Pack
Template: `templates/reports/board_pack.pptx`

Data structure:
```json
{
  "fund_name": "Example Fund",
  "quarter": "Q4 2024",
  "aum": 500000000,
  "performance": {
    "qtd": 2.5,
    "ytd": 8.3,
    "since_inception": 45.2
  },
  "flow_summary": {...},
  "platform_breakdown": [...],
  "key_highlights": [...]
}
```

## Usage Examples

### Render Single Document
```python
from tools.carbone_tools import CarboneTools

carbone = CarboneTools()

result = await carbone.render(
    template="monthly_flows",
    data={
        "client_name": "Example Fund",
        "period": "January 2024",
        "total_inflows": 15000000,
        # ...
    },
    output_format="pdf",
    output_path="/tmp/report.pdf"
)
```

### Batch Generation
```python
result = await carbone.batch_render(
    template="monthly_flows",
    data_list=[
        {"client_name": "Client A", "period": "Jan 2024", ...},
        {"client_name": "Client B", "period": "Jan 2024", ...},
    ],
    output_format="pdf",
    output_dir="/tmp/reports",
    filename_template="{client_name}_{period}"
)
```

### Via MCP
```
"Generate the monthly flows report for Client ABC for January 2024"
→ Claude calls carbone_render_report(
    report_type="monthly_flows",
    client_id="abc",
    period="2024-01"
  )
```

## Creating New Templates

1. Create document in Word/Excel/PowerPoint
2. Add Carbone placeholders: `{d.field_name}`
3. Save to `templates/` directory
4. Test with sample data
5. Document the expected data structure

## Template Best Practices

1. **Use semantic names**: `{d.total_net_flows}` not `{d.tnf}`
2. **Include fallbacks**: `{d.optional_field:or('N/A')}`
3. **Format numbers**: Always use `:formatN()` for numbers
4. **Format dates**: Always use `:formatD()` for dates
5. **Test edge cases**: Empty arrays, null values, large numbers

## Common Issues

### "Field not found"
- Check data structure matches template placeholders
- Verify JSON keys match exactly (case-sensitive)

### Loop not working
- Ensure `[i+1]` is present to end loop
- Check array exists and has items

### PDF conversion fails
- LibreOffice must be installed for PDF conversion
- Check CARBONE_LIBRE_OFFICE_PATH if custom location

## Integration with n8n

```json
{
  "nodes": [
    {
      "name": "Generate Report",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "={{$env.CARBONE_API_URL}}/render",
        "method": "POST",
        "body": {
          "template": "monthly_flows",
          "data": "={{$json.report_data}}",
          "outputFormat": "pdf"
        }
      }
    }
  ]
}
```
