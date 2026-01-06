# 🚀 Enterprise RAG Platform

> **Production-grade document intelligence system** with RAG, analytics, and export capabilities

A comprehensive FastAPI-based platform for document ingestion, retrieval-augmented generation (RAG), CSV analytics, summarization, and intelligent export — built with enterprise-level observability and graceful degradation.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [API Documentation](#-api-documentation)
- [Development](#-development)
- [Testing](#-testing)
- [Deployment](#-deployment)

---

## 🎯 Overview

Enterprise RAG Platform transforms unstructured documents and structured data into actionable intelligence. Upload PDFs, CSVs, or text files, and get instant semantic search, Q&A, analytics, summaries, and professionally formatted exports.

### **What Makes This Platform Different?**

✅ **Graceful Degradation** - System adapts intelligently when components fail  
✅ **Comprehensive Telemetry** - Track every operation with detailed metrics  
✅ **Production-Ready** - PostgreSQL + async architecture + proper error handling  
✅ **Flexible LLM Support** - Works with or without LLMs (extractive fallback)  
✅ **Multi-Format Ingestion** - PDF, CSV, TXT, Markdown, DOCX support  

---

## ✨ Key Features

### 🔍 **Document Intelligence**
- **Multi-format ingestion**: PDF, CSV, TXT, Markdown, DOCX
- **Intelligent chunking**: Configurable strategies with overlap
- **Duplicate detection**: Hash-based deduplication with versioning
- **Metadata extraction**: Automatic enrichment and tagging

### 🤖 **RAG & Retrieval**
- **Semantic search**: Vector similarity with ChromaDB
- **Hybrid retrieval**: Combine semantic + keyword + metadata filters
- **Confidence-based routing**: Adapts strategy based on retrieval quality
- **Citation tracking**: Source attribution for all answers

### 📊 **CSV Analytics**
- **Statistical profiling**: Descriptive stats, distributions, correlations
- **Data quality assessment**: Nulls, duplicates, outliers detection
- **LLM narrative insights**: Optional AI-powered analysis
- **Intelligent caching**: Avoid recomputation with cache hit tracking

### 📄 **Summarization & Insights**
- **Document summarization**: Key points extraction
- **Cross-file insights**: Semantic clustering across documents
- **Topic identification**: Automatic theme detection
- **Multi-document synthesis**: Combine insights from multiple sources

### 📥 **Export Pipeline**
- **Markdown export**: Structured reports
- **PDF generation**: Professional documents
- **Template rendering**: Custom formats
- **Batch processing**: Multiple document exports

### 🛠️ **Agent Orchestration**
- **Multi-tool execution**: Coordinate RAG, ML, analytics
- **Iterative reasoning**: Multi-step problem solving
- **Context management**: Maintain state across tool calls
- **Function calling**: Extensible tool registry

### 🎯 **ML Predictions**
- **Model management**: Load and serve ML models
- **Feature pipeline**: Automated preprocessing
- **Batch inference**: Efficient predictions
- **Cache-aware**: Avoid redundant computations

### 📡 **Observability**
- **Comprehensive telemetry**: Latency, routing, cache metrics
- **Health checks**: Database, vector store, model availability
- **Graceful degradation tracking**: 5-level degradation system
- **Structured logging**: Context-aware log entries

---

## 🏗️ Architecture

```
Client Layer → API Gateway (FastAPI) → Core Services → Data Persistence
                                      ↓
                           [Ingestion | RAG | Analytics]
                           [Summarization | Export | Agent]
                           [ML | Observability]
                                      ↓
                      [PostgreSQL | ChromaDB | Redis | Files]
```

**📐 [View Full Architecture Diagram →](docs/architecture/architecture_diagram.png)**  
**📖 [Read Architecture Overview →](docs/architecture/architecture_overview.md)**

---

## 🚀 Quick Start

### **Prerequisites**

- Python 3.11+
- PostgreSQL 14+
- 2GB+ RAM
- (Optional) Redis for caching

### **1. Clone & Install**

```bash
git clone https://github.com/yourusername/enterprise-rag-platform.git
cd enterprise-rag-platform

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### **2. Database Setup**

```bash
# Create PostgreSQL database
psql -U postgres
CREATE DATABASE rag_platform;
\q

# Run migrations
alembic upgrade head
```

### **3. Configuration**

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
# Minimum required:
#   DB_HOST=localhost
#   DB_USER=postgres
#   DB_PASS=your-password
#   DB_NAME=rag_platform
```

### **4. Run Server**

```bash
# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### **5. Verify**

```bash
# Health check
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs
```

---

## ⚙️ Configuration

### **Environment Variables**

Key configuration options in `.env`:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/rag_platform

# Vector Store
VECTOR_DB_PATH=./data/vector_store

# LLM Provider (none|gemini|openai|ollama|auto)
LLM_PROVIDER=none
# GEMINI_API_KEY=your-key-here

# RAG Settings
CHUNK_SIZE=200
CHUNK_OVERLAP=50
TOP_K_RETRIEVAL=5

# CSV Analytics
ENABLE_LLM_INSIGHTS=false
CSV_CACHE_ENABLED=true

# Uploads
MAX_UPLOAD_SIZE_MB=50
```

**📝 [Full Configuration Reference →](.env.example)**

### **LLM Provider Setup**

**Option 1: No LLM (Lightweight Mode)**
```bash
LLM_PROVIDER=none
```
Platform uses extractive methods only. Perfect for resource-constrained environments.

**Option 2: Google Gemini**
```bash
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-key-here
```

**Option 3: OpenAI**
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=your-key-here
```

**Option 4: Local Ollama**
```bash
LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
```

---

## 📚 API Documentation

### **Interactive Docs**

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### **Key Endpoints**

#### **Document Ingestion**
```http
POST /rag/ingest-file
Content-Type: multipart/form-data

{
  "file": (binary),
  "chunk_size": 200,
  "exists_policy": "skip"
}
```

#### **RAG Query**
```http
POST /rag/answer
Content-Type: application/json

{
  "question": "What are the key findings?",
  "top_k": 5
}
```

#### **CSV Analytics**
```http
GET /analytics/csv/{document_id}?llm_insight_mode=false
```

#### **Document Summarization**
```http
POST /rag/summarize
Content-Type: application/json

{
  "document_id": "abc123-v1"
}
```

#### **Export**
```http
GET /export/report/markdown/{document_id}
GET /export/report/pdf/{document_id}
```

#### **Agent Orchestration**
```http
POST /agent/run
Content-Type: application/json

{
  "query": "Analyze document X and predict outcome Y",
  "max_iterations": 5
}
```

---

## 🛠️ Development

### **Project Structure**

```
enterprise-rag-platform/
├── app/
│   ├── api/              # FastAPI routes
│   ├── rag/              # RAG pipeline
│   ├── analytics/        # CSV analytics
│   ├── core/             # Database, logging, config
│   ├── ingestion/        # Document parsing
│   ├── tools/            # Agent tools
│   └── utils/            # Helpers
├── tests/                # Test suite
├── scripts/              # Utilities
├── docs/                 # Documentation
│   └── architecture/     # Architecture diagrams
├── data/                 # Runtime data (gitignored)
│   ├── uploads/          # User uploads
│   └── vector_store/     # Chroma DB
├── alembic/              # Database migrations
├── .env.example          # Config template
├── requirements.txt      # Dependencies
└── README.md             # You are here
```

### **Development Workflow**

```bash
# Run linting
flake8 app/ tests/
black app/ tests/

# Type checking
mypy app/

# Run tests
pytest tests/ -v

# Coverage report
pytest --cov=app tests/
```

---

## 🧪 Testing

### **Run Tests**

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific module
pytest tests/test_rag.py -v
```

### **Platform Validation**

Run full end-to-end validation:

```bash
# Ensure server is running
python scripts/full_platform_validation.py
```

Validates all subsystems:
- ✅ Ingestion pipeline
- ✅ RAG retrieval & Q&A
- ✅ CSV analytics & caching
- ✅ Summarization
- ✅ Export pipeline
- ✅ Agent orchestration
- ✅ ML predictions
- ✅ Graceful degradation

---

## 🚢 Deployment

### **Production Checklist**

- [ ] Set `ENV=production` in `.env`
- [ ] Use managed PostgreSQL (AWS RDS, Azure Database, etc.)
- [ ] Configure Redis for caching
- [ ] Set up proper secrets management
- [ ] Enable HTTPS with SSL certificates
- [ ] Configure CORS origins
- [ ] Set up monitoring (Sentry, DataDog)
- [ ] Configure backups for PostgreSQL and vector store
- [ ] Set resource limits (CPU, memory)
- [ ] Enable rate limiting

### **Scaling Considerations**

- **Horizontal Scaling**: Run multiple FastAPI instances behind load balancer
- **Database**: Use connection pooling (default: min=5, max=20)
- **Vector Store**: Consider managed ChromaDB or Pinecone
- **Caching**: Redis cluster for high availability
- **Storage**: S3/Azure Blob for file uploads

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **FastAPI** - Modern web framework
- **ChromaDB** - Vector database
- **Sentence Transformers** - Embedding models
- **PostgreSQL** - Reliable data storage

---

**Built with ❤️ for enterprise document intelligence**
