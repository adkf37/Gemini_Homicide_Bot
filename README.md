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

## 🌐 Deploying the Web App Publicly

The Flask interface in `web/web_app.py` is production-ready once you wrap it in a hardened
web server, secure the environment variables, and host it on an internet-facing machine.
Below is a reference workflow that you can adapt to any cloud VM or PaaS provider:

1. **Choose a host** – provision a small Linux VM (e.g., Ubuntu 22.04) on your preferred
   cloud platform or pick a PaaS such as Render, Railway, or Fly.io that can run Python
   web apps.
2. **Clone and configure the project** – install system packages (`python3`, `pip`,
   `git`), pull the repository, and create a Python virtual environment. Install
   dependencies with `pip install -r requirements.txt` and set the `GOOGLE_API_KEY`
   environment variable for the Gemini API.
3. **Run the app with a production WSGI server** – instead of Flask’s built-in server,
   launch Gunicorn (already compatible with `web/web_app.py`):
   ```bash
   pip install gunicorn
   GOOGLE_API_KEY=... gunicorn --bind 0.0.0.0:8000 web.web_app:app
   ```
   Confirm <http://your-server-ip:8000> responds before proceeding.
4. **Add a reverse proxy (optional but recommended)** – configure Nginx or Caddy in
   front of Gunicorn to terminate TLS, serve the static assets in `web/static/`, and
   forward `/` requests to `http://127.0.0.1:8000`. Use Let’s Encrypt or your host’s
   certificate manager for HTTPS.
5. **Persist and monitor** – create a systemd service (on VMs) or the equivalent on your
   platform to keep Gunicorn running, automatically restart on failure, and capture logs.

For container-centric workflows, build a lightweight image from the repo root:

```Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn
COPY . .
ENV GOOGLE_API_KEY=changeme \
    PORT=8000
CMD ["gunicorn", "--bind", "0.0.0.0:${PORT}", "web.web_app:app"]
```

Push the image to your registry and deploy it to a service like Google Cloud Run, AWS
App Runner, or Azure Container Apps—each will route HTTPS traffic to the container.
- **Investigation status**: Arrest rates, domestic cases

## 🚀 Advanced Features

- **Intelligent Parsing**: Robust JSON extraction from LLM responses
- **Error Recovery**: Fallback parsing mechanisms for malformed tool calls
- **Rich Formatting**: Statistics tables, trends, and highlighted insights
- **Debug Mode**: Comprehensive logging for troubleshooting
- **Flexible Queries**: Natural language understanding for various question formats

## 🔄 Migration from RAG

This project evolved from a RAG (Retrieval Augmented Generation) system to an MCP-based approach:
- **Before**: Document embedding and vector similarity search
- **Now**: Structured data analysis with intelligent tool calling
- **Benefits**: More precise answers, better data insights, lower computational overhead
