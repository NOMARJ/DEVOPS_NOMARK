# =============================================================================
# Terraform Remote State Backend (Azure Storage)
# =============================================================================
# Uncomment this configuration to use remote state in Azure Storage.
# This is recommended for production and CI/CD deployments.
#
# Setup:
#   1. Run: ./scripts/setup-terraform-backend.sh
#   2. Uncomment the backend block below
#   3. Run: terraform init -migrate-state
# =============================================================================

# terraform {
#   backend "azurerm" {
#     resource_group_name  = "devops-tfstate-rg"
#     storage_account_name = "devopstfstate${RANDOM_SUFFIX}"
#     container_name       = "tfstate"
#     key                  = "devops-agent.tfstate"
#   }
# }
