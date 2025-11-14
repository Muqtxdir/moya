# MOYA for Research

Multi-agent research paper analysis system built with the [MOYA framework](https://github.com/montycloud/moya).

## Overview

MOYA for Research is an intelligent system that uses specialized AI agents to parse, summarize, and synthesize research papers. It demonstrates multi-agent coordination, tool integration, and observability.

### Features

- **Multi-Agent Architecture**: Four specialized agents (Parser, Summarizer, Synthesis, Chat)
- **Interactive Chat**: Query analyzed papers with conversational AI interface
- **Local LLM Support**: Ollama integration for cost-effective processing
- **PDF Processing**: Hybrid PyMuPDF + PyPDF2 approach for accurate extraction
- **Structured Storage**: SQLite database with proper schema
- **File Outputs**: Individual paper directories + synthesis + mini-survey
- **Comprehensive Logging**: Dual-sink logging (console + trace.jsonl)
- **Reproducibility**: Deterministic runs with fixed temperature
- **CLI Interface**: Beautiful command-line interface with Typer + Rich
- **Docker Support**: Complete containerization with docker-compose
- **MOYA Integration**: Proper tool registry and agent patterns

## System Architecture

```
                  Research Orchestrator
                 (Workflow Coordination)
                  |                    |
                  v                    v                    v
           Parser Agent        Summarizer       Synthesis Agent
           - parse_pdf         - get_paper      - get_all_papers
           - extract_meta      - store_sum      - get_summaries
           - store_paper                        - store_synthesis
                  |                    |                    |
                  +--------------------+--------------------+
                                       v
                                  SQLite DB
                                   + Tools
```

## Agents

### 1. Parser Agent
- Parses PDF files (PyMuPDF for content, PyPDF2 for metadata)
- Extracts title, authors, abstract, year
- Stores papers in database

### 2. Summarizer Agent
- Retrieves papers from database
- Generates structured summaries
- Extracts key findings, methodology, contributions, limitations
- Stores summaries in database

### 3. Synthesis Agent
- Analyzes all papers and summaries
- Identifies common themes
- Finds research gaps
- Proposes future directions
- Stores synthesis in database

### 4. Chat Agent (RAG-Enhanced)
- Interactive Q&A interface for queried analyzed papers
- **Dual-mode operation**: Tools + RAG fallback
- Preloads database contents into context (Retrieval Augmented Generation)
- If tool calling fails, answers directly from context
- Robust for small models that struggle with structured tool calls

## Installation

### Prerequisites
- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- Docker (for Ollama)

### Setup

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd moya
```

2. **Install dependencies with uv**
```bash
uv sync
```

3. **Run Ollama with Docker**
```bash
docker run -d -p 11434:11434 -v ~/.ollama:/root/.ollama --name ollama ollama/ollama
docker exec ollama ollama pull gemma3:1b
```

4. **Place PDF files in `papers/` directory**
```bash
mkdir -p papers
# Copy your research papers (PDF) into papers/
```

## Usage

### Option 1: Docker

The system uses Docker Compose profiles for different use cases:

#### Run Analysis

```bash
# 1. Place PDF files in papers/ directory
mkdir -p papers
cp your-papers/*.pdf papers/

# 2. Run analysis
docker-compose --profile prod up

# 3. View results
ls data/          # Analysis outputs (paper_1/, paper_2/, synthesis.json, mini_survey.md)
ls database/      # SQLite database
ls logs/          # Log files
```

**What happens:**
- Ollama container starts with gemma3:1b model (6GB memory reserved)
- App container analyzes all PDFs in `papers/`
- Results saved to `data/`, `database/`, and `logs/`

#### Development: Live Source Editing

```bash
# Run with source code mounted for live editing
docker-compose --profile dev up

# Your changes in ./src are immediately reflected
```

**What's different:**
- Source code mounted as volume (`./src:/app/src`)
- Debug mode enabled
- Log level set to DEBUG
- No rebuild needed for code changes

#### Interactive Chat

```bash
# Start interactive chat with analyzed papers
docker-compose --profile chat up

# Then interact with the chat interface
```

**Environment Variables:**

Use `.env` file or shell variables:
```bash
# .env file
OLLAMA_MODEL=llama3.2:3b
DEBUG=true
LOG_LEVEL=DEBUG

# Or inline
OLLAMA_MODEL=llama3.2:3b docker-compose --profile prod up
```

**Multiple Profiles:**

```bash
# Run analysis and then chat
docker-compose --profile prod --profile chat up
```

**Ollama Model Management:**

```bash
# Pull a different model
docker-compose exec ollama ollama pull llama3.2:3b

# List available models
docker-compose exec ollama ollama list

# Run with different model
OLLAMA_MODEL=llama3.2:3b docker-compose --profile prod up
```

**Service Management:**

```bash
# Start only Ollama (runs without profile)
docker-compose up ollama

# Stop all services
docker-compose down

# View logs
docker-compose logs -f app
docker-compose logs -f ollama

# Rebuild after Dockerfile changes
docker-compose build
```

### Option 2: CLI (Local Development)

Run from anywhere - the system creates directories relative to your current location:

```bash
# Analyze papers
uv run moya-research analyze

# Custom paths
uv run moya-research analyze \
  --papers-dir /path/to/papers \
  --output-dir /path/to/output \
  --db-dir /path/to/database

# Different model
uv run moya-research analyze --ollama-model llama3.2:3b

# Interactive chat (query the analyzed papers)
uv run moya-research chat

# Chat with custom database
uv run moya-research chat --db-dir /path/to/database

# Help
uv run moya-research --help
uv run moya-research analyze --help
uv run moya-research chat --help
```

**CLI Options:**
- `--papers-dir, -p`: Directory containing PDF research papers (default: papers/)
- `--output-dir, -o`: Directory for analysis outputs (default: data/)
- `--db-dir, -d`: Directory for SQLite database (default: database/)
- `--ollama-url`: Ollama API base URL (default: http://localhost:11434)
- `--ollama-model, -m`: Ollama model to use (default: gemma3:1b)

**Note:** Logs are always written to `logs/trace.jsonl` relative to the current directory.

### Option 3: Interactive Chat

After running the analysis, you can chat with the system to query the results:

```bash
# Start interactive chat
uv run moya-research chat
```

**What you can do in chat:**
- Ask questions about the analyzed papers
- Get summaries of specific papers
- Explore common themes and research gaps
- Query the synthesis and mini-survey
- Compare different papers
- Find specific information from the database

**Example questions:**
- "What are the main themes across all papers?"
- "Can you summarize the first paper?"
- "What research gaps were identified?"
- "Which paper discusses machine learning?"
- "What are the key findings from the synthesis?"

**Chat features:**
- Greets you with paper titles if analysis is done
- Prompts you to run analysis first if no data exists
- Uses database tools to retrieve accurate information
- Conversational interface with context awareness
- Type `exit`, `quit`, or `Ctrl+C` to end the chat

### Option 4: Python Script

```python
from moya_for_research.database import init_db
from moya_for_research.orchestrator import ResearchOrchestrator
from pathlib import Path

# Initialize database
init_db()

# Get PDF paths
papers_dir = Path("papers")
pdf_paths = [str(p) for p in papers_dir.glob("*.pdf")]

# Create orchestrator and run workflow
orchestrator = ResearchOrchestrator()
results = orchestrator.process_papers(pdf_paths)

print(f"Processed {len(results['parsing'])} papers")
print(f"Generated {len(results['summarization'])} summaries")
print(f"Synthesis generated: {'Yes' if results['synthesis'] else 'No'}")
```

## Configuration

Create a `.env` file or set environment variables:

```bash
# Ollama Configuration (Local LLM)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:1b            # Or qwen3:4b, llama3.2:3b, llama3:8b

# Application Settings
DEBUG=False
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR

# LLM Settings
LLM_TEMPERATURE=0.0               # 0.0 = Deterministic (reproducibility)
LLM_MAX_TOKENS=4000               # Max response tokens
MAX_TOOL_ITERATIONS=5             # MOYA tool calling iterations

# Paths (relative to current directory)
DATA_DIR=data        # Analysis outputs
LOG_DIR=logs        # Trace logs
DB_DIR=database     # SQLite database
PAPERS_DIR=papers   # Input PDFs
```

## Output

The system creates a structured output directory with analysis results:

```
data/
  paper_1/
    metadata.json    # Paper title, authors, year, abstract
    summary.json     # Structured summary with findings
  paper_2/
    metadata.json
    summary.json
  ...
  synthesis.json     # Cross-paper analysis with themes, gaps, directions
  mini_survey.md     # Mini-survey (≤800 words) with citations

database/
  research.db        # SQLite database with full data

logs/
  trace.jsonl        # Execution trace in JSON Lines format
```

### 1. Individual Paper Outputs (`data/paper_{id}/`)

Each paper gets its own directory containing:

**metadata.json:**
```json
{
  "paper_id": 1,
  "title": "Paper Title",
  "authors": "Author Names",
  "year": 2024,
  "abstract": "Abstract text...",
  "file_name": "paper.pdf",
  "page_count": 12
}
```

**summary.json:**
```json
{
  "paper_id": 1,
  "summary": "2-3 sentence overview",
  "key_findings": "Main findings...",
  "methodology": "Research methods...",
  "contributions": "Novel contributions...",
  "limitations": "Limitations and future work..."
}
```

### 2. Synthesis Output (`data/synthesis.json`)

Cross-paper analysis:
```json
{
  "synthesis_text": "500-800 word analysis...",
  "common_themes": ["Theme 1", "Theme 2", ...],
  "research_gaps": ["Gap 1", "Gap 2", ...],
  "future_directions": ["Direction 1", "Direction 2", ...],
  "papers_included": [1, 2, 3, 4, 5],
  "paper_count": 5
}
```

### 3. Mini-Survey (`data/mini_survey.md`)

Formatted literature review (≤800 words) with:
- Introduction
- Key Themes (with inline citations [1], [2])
- Research Gaps and Opportunities
- Conclusion
- References

### 4. Database (`database/research.db`)

SQLite database with full relational data:
- `papers`: Complete paper text and metadata
- `summaries`: Detailed summaries linked to papers
- `synthesis`: Cross-paper analysis with mini-survey

### 5. Logs (`logs/trace.jsonl`)

Structured execution trace in JSON Lines format:
```json
{"timestamp": "2025-11-14T00:00:00", "level": "INFO", "message": "..."}
```

## Technology Stack

### Core Framework
- **MOYA**: Multi-agent orchestration framework
- **Ollama**: Local LLM server (gemma3:1b, llama3.2:3b, qwen3:4b)

### PDF Processing
- **PyMuPDF (fitz)**: Fast, accurate content extraction
- **PyPDF2**: Metadata extraction from PDF dictionary

### Storage & Logging
- **SQLAlchemy**: ORM with SQLite
- **Loguru**: Dual-sink logging (console + trace.jsonl)

### CLI & User Experience
- **Typer**: Modern command-line interface
- **Rich**: Beautiful terminal output
- **Tenacity**: Retry logic with exponential backoff

### Development
- **uv**: Fast Python package manager
- **Pydantic Settings**: Environment-based configuration
- **Docker**: Containerization with docker-compose

## Observability

### trace.jsonl
Every operation is logged in JSON Lines format:
```bash
# View logs with jq
cat logs/trace.jsonl | jq '. | select(.level == "ERROR")'

# Count log entries by level
cat logs/trace.jsonl | jq -r '.level' | sort | uniq -c
```

### Database Inspection
```bash
# Open with SQLite browser
sqlite3 database/research.db

# Or use Python
python -c "from moya_for_research.tools import DBTools; print(DBTools.get_all_papers())"

# View individual paper outputs
cat data/paper_1/metadata.json | jq
cat data/paper_1/summary.json | jq

# View synthesis and mini-survey
cat data/synthesis.json | jq
cat data/mini_survey.md
```

## Troubleshooting

### Import Errors
```bash
# Reinstall packages
uv sync --reinstall
```

### Database Locked
```bash
# Close all connections or delete database
rm data/research.db
# Reinitialize
python -c "from moya_for_research.database import init_db; init_db()"
```

### Ollama Connection Issues
```bash
# Check if Ollama is running
docker ps | grep ollama

# Check available models
docker exec ollama ollama list

# Test Ollama API
curl http://localhost:11434/api/generate -d '{"model": "gemma3:1b", "prompt": "test"}'
```

### API Rate Limits
- Reduce `LLM_MAX_TOKENS`
- Add delays between agent calls
- Use cheaper model (gpt-4o-mini) or local model (Ollama)
