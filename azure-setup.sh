#!/bin/bash
# Azure setup script for Taurus Transit API deployment

# Variables
RESOURCE_GROUP="taurus-api-rg"
LOCATION="eastus"
REGISTRY_NAME="taurusregistry"
APP_NAME="taurus-transit-api"
SKU="Basic"
IMAGE_NAME="taurus-transit-api"
IMAGE_TAG="latest"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print header
echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}  Taurus Transit API - Azure Setup   ${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Login to Azure
echo -e "${YELLOW}Logging in to Azure...${NC}"
az login
echo ""

# Create resource group
echo -e "${YELLOW}Creating resource group $RESOURCE_GROUP in $LOCATION...${NC}"
az group create --name $RESOURCE_GROUP --location $LOCATION
echo -e "${GREEN}Resource group created!${NC}"
echo ""

# Create Container Registry
echo -e "${YELLOW}Creating Azure Container Registry $REGISTRY_NAME...${NC}"
az acr create --resource-group $RESOURCE_GROUP --name $REGISTRY_NAME --sku $SKU
echo -e "${GREEN}Container Registry created!${NC}"
echo ""

# Enable admin user for ACR
echo -e "${YELLOW}Enabling admin user for Container Registry...${NC}"
az acr update -n $REGISTRY_NAME --admin-enabled true
echo -e "${GREEN}Admin user enabled!${NC}"
echo ""

# Get ACR credentials
echo -e "${YELLOW}Getting Container Registry credentials...${NC}"
ACR_USERNAME=$(az acr credential show --name $REGISTRY_NAME --query "username" -o tsv)
ACR_PASSWORD=$(az acr credential show --name $REGISTRY_NAME --query "passwords[0].value" -o tsv)
echo -e "${GREEN}Credentials retrieved:${NC}"
echo -e "Username: ${ACR_USERNAME}"
echo -e "Password: ${ACR_PASSWORD}"
echo ""

# Build and push Docker image to ACR
echo -e "${YELLOW}Building and pushing Docker image to ACR...${NC}"
echo -e "This step will be done via GitHub Actions, but you can do it manually with:"
echo -e "${BLUE}docker build -t ${REGISTRY_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG} .${NC}"
echo -e "${BLUE}az acr login --name ${REGISTRY_NAME}${NC}"
echo -e "${BLUE}docker push ${REGISTRY_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}${NC}"
echo ""

# Create Container Apps environment
echo -e "${YELLOW}Creating Container Apps environment...${NC}"
az containerapp env create \
  --name taurus-environment \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION
echo -e "${GREEN}Container Apps environment created!${NC}"
echo ""

# Create Container App
echo -e "${YELLOW}Creating Container App...${NC}"
echo -e "After pushing the image, create the Container App with:"
echo -e "${BLUE}az containerapp create \\${NC}"
echo -e "${BLUE}  --name ${APP_NAME} \\${NC}"
echo -e "${BLUE}  --resource-group ${RESOURCE_GROUP} \\${NC}"
echo -e "${BLUE}  --environment taurus-environment \\${NC}"
echo -e "${BLUE}  --image ${REGISTRY_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG} \\${NC}"
echo -e "${BLUE}  --registry-server ${REGISTRY_NAME}.azurecr.io \\${NC}"
echo -e "${BLUE}  --registry-username ${ACR_USERNAME} \\${NC}"
echo -e "${BLUE}  --registry-password ${ACR_PASSWORD} \\${NC}"
echo -e "${BLUE}  --target-port 8000 \\${NC}"
echo -e "${BLUE}  --ingress external \\${NC}"
echo -e "${BLUE}  --query properties.configuration.ingress.fqdn${NC}"
echo ""

# Store GitHub secrets
echo -e "${YELLOW}For GitHub Actions, add these secrets to your repository:${NC}"
echo -e "${BLUE}AZURE_CREDENTIALS${NC} - Create with: az ad sp create-for-rbac --name 'taurus-api' --role contributor --scopes /subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP --sdk-auth"
echo -e "${BLUE}ACR_USERNAME${NC} - ${ACR_USERNAME}"
echo -e "${BLUE}ACR_PASSWORD${NC} - ${ACR_PASSWORD}"
echo ""

echo -e "${GREEN}Setup script completed!${NC}"
echo -e "${GREEN}Check the README.md file for more information on deployment.${NC}" 