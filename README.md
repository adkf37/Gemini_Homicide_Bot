# Gemini LLM with MCP Tools for Homicide Data Analysis

This project integrates Google's Gemini 1.5 Pro with **Model Context Protocol (MCP)** tools for intelligent querying of homicide data. The system allows users to ask natural language questions about crime statistics and automatically calls appropriate data analysis tools.

## 🚀 Features

- **Intelligent Tool Calling**: Ask natural questions like "What location had the most homicides?" and the LLM automatically calls the right tools
- **MCP Integration**: Uses Model Context Protocol for structured tool calling and data access  
- **Homicide Data Analysis**: Comprehensive analysis of homicide records from 2001 to present
- **Gemini Pro Integration**: Uses Google's Gemini 1.5 Pro API for higher-quality responses
- **Interactive CLI**: User-friendly command-line interface with helpful commands
- **Robust Parsing**: Advanced JSON parsing for reliable tool call extraction
- **Rich Data Visualization**: Formatted output with statistics, trends, and insights

## 🎯 What You Can Ask

The system can intelligently answer questions like:
- **"What location had the most homicides?"** → Automatically gets overall statistics
- **"How many homicides were there in 2023?"** → Calls year-specific data tool
- **"Find homicides on Michigan Avenue"** → Searches by location
- **"What does IUCR code mean?"** → Explains crime classification codes
- **"Show me arrest statistics"** → Retrieves arrest rate data and trends

## 🛠️ Quick Start

### 1. Enable Gemini API Access
Create a Google AI Studio project and generate an API key with access to Gemini 1.5 Pro.

### 2. Set Your API Key
```bash
export GOOGLE_API_KEY="your_api_key_here"
```
On Windows PowerShell:
```powershell
$Env:GOOGLE_API_KEY="your_api_key_here"
```

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
- **`mcp_integration.py`** - MCP protocol implementation and tool definitions
- **`homicide_mcp.py`** - Homicide data handler and analysis functions
- **`llama_client.py`** - Gemini client with tool calling capabilities

### Configuration & Setup
- **`config.py`** - Configuration management system  
- **`config.yaml`** - Model and application settings
- **`requirements.txt`** - Python dependencies
- **`setup.py`** / **`setup.ps1`** - Setup scripts

### Data & Testing
- **`knowledge_base/`** - Homicide data and schema files
  - `Homicides_2001_to_present.csv` - Main dataset (12,657+ records)
  - `homicides_schema.md` - Data schema documentation
- **`test_*.py`** - Test scripts for MCP functionality
- **`data/chroma_db/`** - Vector database storage (legacy from RAG version)

## 🔧 Available MCP Tools

The system provides these intelligent data analysis tools:

| Tool | Purpose | Example Question |
|------|---------|------------------|
| **`get_homicide_statistics`** | Overall stats, trends, top locations | "What location had the most homicides?" |
| **`get_homicides_by_year`** | Year-specific data | "How many homicides in 2023?" |
| **`search_by_location`** | Location-based search | "Find homicides on State Street" |
| **`get_iucr_info`** | Crime code information | "What does IUCR mean?" |

## 💬 Usage Examples

### Interactive Mode
```
💬 You: What location had the most homicides?
🤔 Question: "What location had the most homicides?"
🧠 Detected data question - using intelligent MCP...
🔧 Calling tool: get_homicide_statistics with args: {}
🤖 Assistant: Based on the homicide data analysis, the 11th District had the most homicides with 1,247 cases, followed by the 15th District with 891 cases...
```

### Manual Tool Calls
```
💬 You: /mcp get_homicides_by_year 2023
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
  name: "gemini-1.5-pro-latest"        # Gemini model name
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
  --set-secrets=GOOGLE_API_KEY=gemini-api-key:latest \
  --memory 512Mi \
  --cpu 1
```

Cloud Run will:
- Build the Docker image from the `Dockerfile`
- Deploy to a public HTTPS URL
- Auto-scale from 0 to 10 instances based on traffic
- Inject `GOOGLE_API_KEY` from Secret Manager

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
