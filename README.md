# Taurus Astrological Transit API

A powerful API for calculating astrological transits, built with Flask and designed for deployment to Azure. This API can calculate planetary transits using either Swiss Ephemeris (high precision) or AstroSeek (web-based) methods.

## Features

- **Transit Calculations:** Get accurate planetary transit forecasts for any time period
- **Dual Calculation Methods:** Choose between Swiss Ephemeris (offline) or AstroSeek (online) calculation methods
- **Standardized Coordinate Format:** Uses a simple latitude/longitude format (e.g., "51n39 0w24")
- **JSON API:** Easily integrate transit data into your applications
- **Azure Ready:** Deployment-ready for Microsoft Azure

## API Usage

The Taurus Transit Calculator now includes a REST API for easy integration with other applications. You can access transit calculations through HTTP requests without needing to run the command-line application directly.

### API Endpoints

#### `GET /transits`

Calculate transits based on query parameters.

**Required Parameters:**
- `birth_date` - Birth date in YYYY-MM-DD format
- `birth_time` - Birth time in HH:MM format (24-hour format)
- `birth_coordinates` - Birth coordinates in "51n39 0w24" format
- `month` - Target month in YYYY-MM format

**Optional Parameters:**
- `current_coordinates` - Current coordinates in "51n39 0w24" format (defaults to birth coordinates)
- `house_system` - House system to use (W for Whole Sign, P for Placidus, defaults to W)
- `astroseek` - Set to "1" to use AstroSeek calculation (defaults to Swiss Ephemeris)
- `aspect_set` - Set of aspects to use (major, minor, all; defaults to major)

**Example Request:**
```
GET /transits?birth_date=1990-01-01&birth_time=12:00&birth_coordinates=51n30%200w10&month=2024-09
```

#### `POST /transits`

Calculate transits with JSON payload.

**Example Request:**
```json
POST /transits
Content-Type: application/json

{
  "birth_date": "1990-01-01",
  "birth_time": "12:00",
  "birth_coordinates": "51n30 0w10",
  "month": "2024-09",
  "house_system": "W",
  "astroseek": "0"
}
```

**Example Response:**
```json
{
  "parameters": {
    "birth_date": "1990-01-01",
    "birth_time": "12:00",
    "birth_coordinates": "51n30 0w10",
    "house_system": "W",
    "period": "2024-09",
    "current_coordinates": "51n30 0w10",
    "aspect_set": "major",
    "calculation_method": "Swiss Ephemeris"
  },
  "total_transits": 25,
  "transits": [
    {
      "date_display": "Sep 2, 15:30",
      "date": "2024-09-02",
      "time": "15:30",
      "transit_planet": "Moon",
      "transit_planet_symbol": "☽",
      "is_retrograde": false,
      "aspect": "conjunction",
      "aspect_symbol": "☌",
      "natal_planet": "Venus",
      "natal_planet_symbol": "♀",
      "position": "♉ 12°30'",
      "house": "H3",
      "interpretation": "Your emotions are in harmony with your sense of beauty and love..."
    },
    // ... more transits ...
  ]
}
```

#### `GET /health`

Health check endpoint that returns the service status.

**Example Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### Running the API Locally

The Taurus API can be run locally using Docker, which simplifies dependency management:

1. Make sure you have Docker and Docker Compose installed on your system
2. Clone the repository and navigate to the project directory
3. Build and start the API using Docker Compose:
   ```
   docker-compose up --build
   ```
4. The API will be available at `http://localhost:5000`
5. Test the API using the provided test script:
   ```
   python test-api.py
   ```

### Deploying to Azure

The Taurus Transit API can be deployed to Azure Container Apps for scalable and reliable hosting:

1. Prerequisites:
   - Azure account
   - Azure CLI installed
   - Docker installed

2. Setup Azure Resources:
   - Run the provided Azure setup script:
     ```
     ./azure-setup.sh
     ```
   - This script will create:
     - Resource Group
     - Azure Container Registry
     - Container Apps environment

3. GitHub Actions Deployment:
   The repository includes GitHub Actions workflows for automatic deployment:
   
   - Set up these GitHub secrets:
     - `AZURE_CREDENTIALS`: Service principal credentials (created via the azure-setup.sh script)
     - `ACR_USERNAME`: Azure Container Registry username
     - `ACR_PASSWORD`: Azure Container Registry password

   - Push changes to the main branch to trigger automatic deployment

4. Manual Deployment:
   You can also deploy manually:
   
   ```bash
   # Build and tag the Docker image
   docker build -t taurusregistry.azurecr.io/taurus-transit-api:latest .
   
   # Log in to Azure Container Registry
   az acr login --name taurusregistry
   
   # Push the image
   docker push taurusregistry.azurecr.io/taurus-transit-api:latest
   
   # Update the Container App
   az containerapp update \
     --name taurus-transit-api \
     --resource-group taurus-api-rg \
     --image taurusregistry.azurecr.io/taurus-transit-api:latest
   ```

### Troubleshooting

- **API Returns 500 Error**: Check the logs in Azure Portal or run the container locally to debug
- **Selenium Issues**: Ensure the Docker container has Chrome installed and configured correctly
- **Missing Transits**: Verify your coordinates are in the correct format and the birth data is valid

## Local Development Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation Steps

1. Clone the repository:
   ```
   git clone <repository-url>
   cd taurus
   ```

2. Create and activate a virtual environment (optional but recommended):
   ```
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the development server:
   ```
   python app.py
   ```
   
   The API will be available at http://localhost:5000

### Testing Locally

Once the server is running, you can test it using curl, Postman, or your web browser:

```
curl "http://localhost:5000/transits?birth_date=2001-05-05&birth_time=10:23&birth_coordinates=51n39+0w24&month=2025-08"
```

## Azure Deployment Instructions

### Prerequisites

- Azure account with active subscription
- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) installed
- Git (to clone the repository)

### Deployment Steps

1. **Login to Azure**

   ```
   az login
   ```

2. **Create a Resource Group**

   ```
   az group create --name TaurusResourceGroup --location eastus
   ```

3. **Create an App Service Plan**

   ```
   az appservice plan create --name TaurusAppServicePlan --resource-group TaurusResourceGroup --sku B1 --is-linux
   ```

4. **Create a Web App**

   ```
   az webapp create --resource-group TaurusResourceGroup --plan TaurusAppServicePlan --name taurus-transit-api --runtime "PYTHON:3.9"
   ```

5. **Configure the App**

   ```
   az webapp config set --resource-group TaurusResourceGroup --name taurus-transit-api --startup-file "gunicorn --bind=0.0.0.0 --timeout 600 app:app"
   ```

6. **Deploy Your Code**

   Method 1: Deploy from local Git repository:
   ```
   az webapp deployment source config-local-git --name taurus-transit-api --resource-group TaurusResourceGroup
   
   # Add Azure as a remote repository
   git remote add azure <URL_from_previous_command>
   
   # Push to Azure
   git push azure main
   ```

   Method 2: Deploy using ZIP deployment:
   ```
   # Compress your application files
   zip -r taurus_app.zip .
   
   # Deploy the ZIP file
   az webapp deployment source config-zip --resource-group TaurusResourceGroup --name taurus-transit-api --src taurus_app.zip
   ```

7. **Configure Environment Variables (if needed)**

   ```
   az webapp config appsettings set --resource-group TaurusResourceGroup --name taurus-transit-api --settings "PORT=8000"
   ```

8. **Access Your API**

   Your API should now be available at:
   ```
   https://taurus-transit-api.azurewebsites.net/
   ```

### Additional Azure Deployment Options

#### Deploy using GitHub Actions

1. Fork this repository to your GitHub account
2. Go to Azure Portal and navigate to your app service
3. Under Deployment Center, choose GitHub
4. Connect to your GitHub account and select your repository
5. Configure the workflow as needed
6. GitHub Actions will automatically deploy your app when you push to the main branch

#### Deploy using Visual Studio Code

1. Install the Azure App Service extension in VS Code
2. Sign in to your Azure account
3. Right-click on your web app in Azure Explorer
4. Select "Deploy to Web App..." and follow the prompts

## Troubleshooting

### Common Issues

1. **Selenium/Chrome Driver Issues**
   - The AstroSeek method requires Chrome and chromedriver.
   - If using AstroSeek on Azure, you may need to configure additional settings or switch to headless mode.

2. **Timezone Issues**
   - If experiencing timezone problems, check that the timezonefinder package is working correctly.

3. **Performance Issues**
   - Calculating many transits can be resource-intensive. Consider increasing the timeout settings:
     ```
     az webapp config set --resource-group TaurusResourceGroup --name taurus-transit-api --generic-configurations "{"maxRequestBodySize":"100000000","requestTimeout":"00:10:00"}"
     ```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 