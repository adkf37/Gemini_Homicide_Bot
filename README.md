# Gemini MCP Tools for Chicago Homicide and Public Data Analysis

This project integrates Google's Gemini API with **Model Context Protocol (MCP)** tools for deterministic analysis of Chicago homicide, census, socioeconomic, and property data. The default model in `config.yaml` is `gemini-2.5-flash-lite`; the model can be changed without changing the MCP tool layer.

## 🚀 Features

- **Intelligent Tool Calling**: Ask natural questions like "What location had the most homicides?" and the LLM automatically calls the right tools
- **MCP Integration**: Uses Model Context Protocol-style schemas for structured tool calling and data access
- **Homicide Data Analysis**: Comprehensive analysis of homicide records from 2001 to present
- **Cross-Domain Operators**: Deterministic joins for homicide rates per 100,000 residents, homicide concentration versus socioeconomic indicators, and district trend comparisons
- **Gemini Integration**: Uses Google's Gemini API for natural-language planning and answer synthesis
- **Interactive CLI**: User-friendly command-line interface with helpful commands
- **Robust Parsing**: Advanced JSON parsing for reliable tool call extraction
- **Traceable Tool Use**: Per-iteration traces plus top-level summaries for web reporting and evaluation

## 🎯 What You Can Ask

The system can intelligently answer questions like:
- **"Which community areas had the highest homicide rate per 100,000 in 2023?"** -> Joins homicides to census population
- **"Where are domestic homicides concentrated relative to hardship index?"** -> Joins homicides to socioeconomic indicators
- **"Which districts changed most from 2020-2021 to 2022-2023?"** -> Compares district-period trends
- **"What location had the most homicides?"** → Automatically gets overall statistics
- **"How many homicides were there in 2023?"** → Calls year-specific data tool
- **"Find homicides on Michigan Avenue"** → Searches by location
- **"What does IUCR code mean?"** → Explains crime classification codes
- **"Show me arrest statistics"** → Retrieves arrest rate data and trends

## 🛠️ Quick Start

### 1. Enable Gemini API Access
Create a Google AI Studio project and generate an API key with access to the Gemini model configured in `config.yaml`.

### 2. Set Your API Key For Local Development
```bash
export GOOGLE_API_KEY="your_api_key_here"
```
On Windows PowerShell:
```powershell
$Env:GOOGLE_API_KEY="your_api_key_here"
```

Do not store the key in a checked-in or long-lived `.env` file. In Cloud Run,
the app reads the key directly from Google Secret Manager.

### 3. Install Python Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Your Model
Edit `config.yaml` to set your preferred model:
```yaml
model:
  name: "gemini-2.5-flash-lite"
  temperature: 0.7
  max_tokens: 2048
```

### 5. Run the System
```powershell
python main.py
```

### 6. Launch the Web Chat Interface

Run the Flask server to interact with the bot from a browser:

```bash
python -m web.web_app
```

Then open <http://localhost:8000> to start chatting. Use the toggle in the footer to decide whether Gemini should call MCP tools for structured homicide data.

## 📁 Project Structure

### Core Files
- **`main.py`** - Main application with interactive CLI and MCP integration
- **`intelligent_mcp.py`** - Intelligent MCP handler for tool calling and response parsing
- **`mcp_integration.py`** - MCP domain registry and tool dispatch
- **`homicide_mcp.py`** - Homicide data handler and analysis functions
- **`cross_domain_mcp.py`** - Joined homicide/census/socioeconomic trend and rate operators
- **`llama_client.py`** - Gemini client with tool calling capabilities

### Configuration & Setup
- **`config.py`** - Configuration management system  
- **`config.yaml`** - Model and application settings
- **`requirements.txt`** - Python dependencies
- **`setup.py`** / **`setup.ps1`** - Setup scripts

### Data & Testing
- **`knowledge_base/`** - Source datasets, schema files, and community-area lookup data
  - `Homicides_2001_to_present.csv` - Main dataset (12,657+ records)
  - `homicides_schema.md` - Data schema documentation
- **`test_*.py`** - Test scripts for MCP functionality
- **`data/cache/`** - Cached structured public-data fetches

## 🔧 Available MCP Tools

The system provides these intelligent data analysis tools:

| Tool | Purpose | Example Question |
|------|---------|------------------|
| **`query_homicides_advanced`** | Counts, filters, rankings, locations, arrests, domestic cases | "Which ward had the most homicides in 2023?" |
| **`get_iucr_info`** | Crime code information | "What does IUCR mean?" |
| **`query_census_demographics`** | Population, income, race/ethnicity, age data | "What is the population of Austin?" |
| **`query_socioeconomic`** | Poverty, unemployment, income, education, hardship | "Which areas have the highest hardship index?" |
| **`query_property_values`** | Residential property sales and trends | "What are home prices in Lincoln Park?" |
| **`analyze_homicide_rates_by_community_area`** | Homicide rates per 100,000 residents | "Highest homicide rate per capita in 2023?" |
| **`analyze_homicide_socioeconomic_context`** | Homicides joined to socioeconomic indicators | "Domestic homicide concentration relative to hardship?" |
| **`compare_homicide_district_trends`** | District period-over-period comparisons | "Which districts increased most from 2020-2021 to 2022-2023?" |
| **`analyze_homicide_rate_population_change`** | Rate change versus population change where multi-year census data exists | "Did homicide rates rise where population fell?" |

## 💬 Usage Examples

### Interactive Mode
```
💬 You: What location had the most homicides?
🤔 Question: "What location had the most homicides?"
🧠 Detected data question - using intelligent MCP...
Calling tool: query_homicides_advanced with args: {"group_by": "district"}
🤖 Assistant: Based on the homicide data analysis, the 11th District had the most homicides with 1,247 cases, followed by the 15th District with 891 cases...
```

### Manual Tool Calls
```
You: /mcp query_homicides_advanced {"start_year": 2023, "end_year": 2023}
📋 MCP Result: 
📅 Homicides in 2023
Total records: 617
Arrests made: 289 (46.8%)
...
```

### Commands Available
- **`/help`** - Show all available commands
- **`/mcp-tools`** - List available MCP tools  
- **`/mcp <tool> [args]`** - Manual tool execution
- **`/notools <question>`** - Use base model without tools
- **`/config`** - Show current configuration
- **`/temp <value>`** - Adjust response creativity (0.0-2.0)

## ⚙️ Configuration

The `config.yaml` file controls model behavior:

```yaml
model:
  name: "gemini-2.5-flash-lite"        # Gemini model name
  temperature: 0.7                     # Response creativity (0.0-2.0)
  max_tokens: 2048                    # Maximum response length
  top_p: 0.9                          # Nucleus sampling
  context_window: 8192                # Effective context size used for prompts

app:
  debug: false              # Enable debug logging
  interactive: true         # Start in interactive mode
```

## 🧠 How It Works

1. **Question Detection**: System analyzes input for homicide-related keywords
2. **Tool Selection**: LLM determines which MCP tool(s) to call based on the question
3. **Tool Execution**: System calls appropriate data analysis functions
4. **Response Synthesis**: LLM formulates a natural language answer based on the data
5. **Result Display**: Formatted output with statistics and insights

## 📊 Data Source

The system analyzes Chicago homicide data including:
- **12,657+ homicide records** from 2001 to present
- **Case details**: Date, location, arrest status, case numbers
- **Geographic data**: Districts, beats, coordinates
- **Classification**: IUCR codes, primary/secondary types

## 🌐 Deploying to Google Cloud Run

The application ships with a `Dockerfile` and GitHub Actions workflow for automated deployment to Google Cloud Run.

### Prerequisites

1. **Google Cloud Project**
   - Create a project at [console.cloud.google.com](https://console.cloud.google.com)
   - Enable Cloud Run API and Artifact Registry API
   - Note your project ID

2. **Gemini API Key**
   - Get your key from [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Store it in Google Secret Manager:
     ```bash
     gcloud secrets create gemini-api-key --data-file=- <<< "YOUR_API_KEY_HERE"
     ```
   - Grant the Cloud Run runtime service account access to that secret:
     ```bash
     PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)')
     gcloud secrets add-iam-policy-binding gemini-api-key \
       --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
       --role="roles/secretmanager.secretAccessor"
     ```

3. **Workload Identity Federation (for CI/CD)**
   - Set up Workload Identity Federation to allow GitHub Actions to deploy
   - Follow [Google's guide](https://github.com/google-github-actions/auth#setting-up-workload-identity-federation)
   - Required GitHub secrets:
     - `GCP_PROJECT_ID`: Your Google Cloud project ID
     - `WIF_PROVIDER`: Workload Identity Provider resource name
     - `WIF_SERVICE_ACCOUNT`: Service account email for deployment

### Manual Deployment

Deploy directly from your local machine:

```bash
# Authenticate with Google Cloud
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Build and deploy
gcloud run deploy gemini-homicide-bot \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --update-env-vars=GOOGLE_API_KEY_SECRET_REF=gemini-api-key,GCP_PROJECT_ID=YOUR_PROJECT_ID \
  --memory 512Mi \
  --cpu 1
```

Cloud Run will:
- Build the Docker image from the `Dockerfile`
- Deploy to a public HTTPS URL
- Auto-scale from 0 to 10 instances based on traffic
- Read the Gemini API key directly from Secret Manager at startup

### Automated Deployment with GitHub Actions

The repository includes `.github/workflows/deploy-cloud-run.yml` that automatically:
1. Runs unit tests on every push
2. Builds and pushes a Docker image to Artifact Registry
3. Deploys to Cloud Run on pushes to `main`

**Setup:**
1. Configure the GitHub secrets listed above
2. Push to the `main` branch
3. GitHub Actions will handle the rest
4. Check the Actions tab for deployment status and service URL

### Local Testing with Docker

Test the containerized app locally:

```bash
# Build the image
docker build -t gemini-homicide-bot .

# Run locally
docker run -p 8080:8080 \
  -e GOOGLE_API_KEY="your-api-key" \
  gemini-homicide-bot

# Test the health endpoint
curl http://localhost:8080/api/health
```

### Alternative Deployment Options

**Render / Railway / Fly.io:**
- Connect your GitHub repo
- Set `GOOGLE_API_KEY` environment variable
- Deploy from `Dockerfile` or use build command: `gunicorn --bind 0.0.0.0:$PORT web.web_app:app`

**Self-hosted VM:**
- Clone repo and install dependencies
- Run with Gunicorn behind Nginx for HTTPS
- Use systemd for process management

## 🧪 Testing

### Unit Tests

Run deterministic tests against the homicide data MCP:

```bash
pip install pytest
pytest tests/test_homicide_mcp.py -v
```

These tests use a small fixture dataset (`tests/fixtures/mini_homicides.csv`) to validate:
- Data loading and normalization
- Query filtering (year, district, ward, arrest status, domestic)
- Grouping and aggregation logic
- Edge cases and error handling

### LLM Performance Testing

Evaluate different Gemini models on complex queries:

```bash
python test_llm_performance.py
```

This comprehensive test suite includes:
- **Simple queries**: Single-parameter tool calls (e.g., "How many homicides in 2023?")
- **"Which X most" queries**: Requires correct `group_by` parameter extraction
- **Top N queries**: Tests `top_n` parameter parsing
- **Complex multi-criteria**: Multiple filters + grouping (e.g., "Top 3 districts with non-domestic homicides where no arrests were made, 2015-2019")
- **Negative cases**: Ensures model doesn't call tools for non-homicide questions
- **Year range variations**: Tests different phrasings ("from X to Y", "between X and Y")
- **Synonym handling**: "murders", "killings", "homicides"
- **Answer consistency validation**: Checks if LLM's answer matches tool output

Results are saved to `llm_test_results_<timestamp>.json` with:
- Per-model pass rates
- Category breakdowns
- Parameter extraction accuracy
- Response times
- Detailed failure reasons

**Configure models to test:**
Edit `model_configs.yaml` to add/remove Gemini models for evaluation.

## 🚀 Advanced Features

- **Intelligent Parsing**: Robust JSON extraction from LLM responses
- **Error Recovery**: Fallback parsing mechanisms for malformed tool calls
- **Rich Formatting**: Statistics tables, trends, and highlighted insights
- **Debug Mode**: Comprehensive logging for troubleshooting
- **Flexible Queries**: Natural language understanding for various question formats
- **Automated Testing**: CI runs unit tests on every push; comprehensive LLM eval suite

## 🔄 Migration from RAG

This project evolved from a RAG (Retrieval Augmented Generation) system to an MCP-based approach:
- **Before**: Document embedding and vector similarity search
- **Now**: Structured data analysis with intelligent tool calling
- **Benefits**: More precise answers, better data insights, lower computational overhead
