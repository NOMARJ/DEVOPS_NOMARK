# Data Validation Skill

> Validate, clean, and score data quality for FlowMetrics platform ingestion.

## When to Use

- Validating SFTP file uploads
- Checking data quality before processing
- Cleaning and transforming raw platform data
- Generating data quality scores and reports

## Prerequisites

- pandas
- pydantic or pandera for schema validation
- Access to platform schema definitions

## Validation Pipeline

```
Raw Data → Schema Validation → Business Rules → Quality Scoring → Clean Data
```

## Schema Validation

### Platform Schemas

Each wealth platform has a defined schema:

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from decimal import Decimal

class AsgardFlowRecord(BaseModel):
    """Asgard platform flow record schema."""
    
    account_number: str = Field(..., min_length=6, max_length=20)
    transaction_date: date
    transaction_type: str = Field(..., pattern="^(BUY|SELL|SWITCH_IN|SWITCH_OUT)$")
    amount: Decimal = Field(..., gt=0)
    fund_code: str = Field(..., min_length=3, max_length=10)
    adviser_code: Optional[str] = None
    
    class Config:
        extra = "forbid"  # Reject unknown fields
```

### Using Pandera for DataFrame Validation

```python
import pandera as pa
from pandera import Column, Check

asgard_schema = pa.DataFrameSchema({
    "account_number": Column(str, Check.str_length(6, 20)),
    "transaction_date": Column(pa.DateTime),
    "transaction_type": Column(str, Check.isin(["BUY", "SELL", "SWITCH_IN", "SWITCH_OUT"])),
    "amount": Column(float, Check.gt(0)),
    "fund_code": Column(str, Check.str_length(3, 10)),
    "adviser_code": Column(str, nullable=True),
})

# Validate
validated_df = asgard_schema.validate(df, lazy=True)
```

## Business Rules

### Rule Definitions

```python
VALIDATION_RULES = {
    "amount_reasonable": {
        "description": "Transaction amount within reasonable range",
        "check": lambda x: 0.01 <= x <= 100_000_000,
        "severity": "warning",
    },
    "future_date": {
        "description": "Transaction date not in future",
        "check": lambda x: x <= date.today(),
        "severity": "error",
    },
    "duplicate_check": {
        "description": "No duplicate transactions",
        "check": "unique_on:account_number,transaction_date,amount",
        "severity": "error",
    },
}
```

### Applying Rules

```python
def validate_business_rules(df: pd.DataFrame, rules: dict) -> ValidationResult:
    """Apply business rules to dataframe."""
    
    errors = []
    warnings = []
    
    for rule_name, rule in rules.items():
        if callable(rule["check"]):
            # Column-level check
            mask = ~df[rule["column"]].apply(rule["check"])
            invalid_rows = df[mask]
            
            if len(invalid_rows) > 0:
                issue = {
                    "rule": rule_name,
                    "description": rule["description"],
                    "affected_rows": len(invalid_rows),
                    "sample": invalid_rows.head(5).to_dict("records"),
                }
                
                if rule["severity"] == "error":
                    errors.append(issue)
                else:
                    warnings.append(issue)
    
    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
```

## Data Quality Scoring

### Quality Dimensions

| Dimension | Weight | Checks |
|-----------|--------|--------|
| Completeness | 25% | Required fields populated |
| Accuracy | 25% | Values within expected ranges |
| Consistency | 20% | Cross-field validations pass |
| Uniqueness | 15% | No unexpected duplicates |
| Timeliness | 15% | Data within expected date range |

### Scoring Function

```python
def calculate_quality_score(df: pd.DataFrame, config: dict) -> QualityScore:
    """Calculate overall data quality score."""
    
    scores = {}
    
    # Completeness
    required_fields = config["required_fields"]
    completeness = df[required_fields].notna().mean().mean()
    scores["completeness"] = completeness
    
    # Accuracy (values in expected ranges)
    accuracy_checks = 0
    accuracy_passes = 0
    for field, rules in config["accuracy_rules"].items():
        if field in df.columns:
            accuracy_checks += 1
            if df[field].between(rules["min"], rules["max"]).mean() > 0.95:
                accuracy_passes += 1
    scores["accuracy"] = accuracy_passes / max(accuracy_checks, 1)
    
    # Uniqueness
    key_fields = config["unique_key"]
    duplicates = df.duplicated(subset=key_fields).sum()
    scores["uniqueness"] = 1 - (duplicates / len(df))
    
    # Weighted average
    weights = config["weights"]
    overall = sum(scores[k] * weights[k] for k in scores)
    
    return QualityScore(
        overall=round(overall * 100, 1),
        dimensions=scores,
        record_count=len(df),
        timestamp=datetime.utcnow(),
    )
```

## Validation Report

### Generate Report

```python
def generate_validation_report(
    df: pd.DataFrame,
    schema_result: SchemaValidationResult,
    business_result: BusinessRuleResult,
    quality_score: QualityScore,
) -> ValidationReport:
    """Generate comprehensive validation report."""
    
    return ValidationReport(
        summary={
            "total_records": len(df),
            "valid_records": len(df) - len(schema_result.errors),
            "quality_score": quality_score.overall,
            "status": "passed" if quality_score.overall >= 80 else "review_required",
        },
        schema_validation={
            "passed": schema_result.valid,
            "errors": schema_result.errors,
        },
        business_rules={
            "errors": business_result.errors,
            "warnings": business_result.warnings,
        },
        quality_dimensions=quality_score.dimensions,
        recommendations=generate_recommendations(schema_result, business_result),
    )
```

## Integration with n8n

### Validation Workflow Node

```json
{
  "name": "Validate Data",
  "type": "n8n-nodes-base.function",
  "parameters": {
    "functionCode": "// Call validation API\nconst response = await $http.request({\n  method: 'POST',\n  url: `${process.env.API_URL}/validate`,\n  body: {\n    file_id: $json.file_id,\n    platform: $json.platform,\n    strict: true\n  }\n});\n\nreturn [{json: response}];"
  }
}
```

### Conditional Processing

```
IF quality_score >= 80:
    → Continue to processing
ELSE IF quality_score >= 60:
    → Flag for review, continue
ELSE:
    → Reject, notify ops team
```

## Error Handling

### Common Validation Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| `SCHEMA_MISMATCH` | Column missing or wrong type | Check platform export settings |
| `DUPLICATE_KEY` | Same transaction uploaded twice | Dedupe before processing |
| `FUTURE_DATE` | Date after today | Check date format/timezone |
| `INVALID_AMOUNT` | Negative or zero amount | Review source data |

### Error Response Format

```json
{
  "valid": false,
  "error_count": 5,
  "errors": [
    {
      "row": 42,
      "field": "amount",
      "value": -500,
      "rule": "amount_positive",
      "message": "Amount must be positive"
    }
  ],
  "quality_score": 72.5,
  "can_proceed": false
}
```

## Best Practices

1. **Validate early**: Check data immediately on upload
2. **Fail fast**: Reject obviously bad files quickly
3. **Log everything**: Keep validation history for debugging
4. **Score, don't just pass/fail**: Quality scores help track trends
5. **Automate corrections**: Auto-fix common issues (trimming, date formats)
