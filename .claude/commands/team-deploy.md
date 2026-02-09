---
description: "Spawn an agent team for deployment preparation"
---

# Team: Deployment Preparation

Create an agent team to prepare for deployment. Spawn teammates:

1. **qa-verifier**: Run complete verification stack across all components. Generate a verification report. Block if any checks fail.

2. **security-reviewer**: Final security scan before deployment. Check for exposed secrets, open ports, missing auth, and Key Vault references. Generate security sign-off.

3. **infra-specialist**: Run `terraform plan` to preview infrastructure changes. Review the plan output for unexpected changes. Verify resource sizing and cost implications.

4. **workflow-builder**: Verify n8n workflow JSON validity. Check webhook endpoints and notification pipelines are correctly configured. Verify Ralph agent script is up to date.

## Deployment Checklist

Each teammate validates their domain and reports ready/not-ready:

- [ ] All tests pass (qa-verifier)
- [ ] No security findings above Medium (security-reviewer)
- [ ] Terraform plan shows expected changes only (infra-specialist)
- [ ] Workflows and integrations validated (workflow-builder)
- [ ] No uncommitted changes on any branch
- [ ] All tasks in shared list are complete

## Gate

The lead should NOT approve deployment unless all teammates report ready.

$ARGUMENTS
