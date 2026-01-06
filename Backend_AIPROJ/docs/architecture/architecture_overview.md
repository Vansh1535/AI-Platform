# Enterprise RAG Platform - System Architecture

## Overview

The Enterprise RAG Platform is a production-grade document intelligence system built on FastAPI, providing enterprise-level document ingestion, retrieval-augmented generation (RAG), analytics, and export capabilities with comprehensive observability.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│  Web UI / API Clients / Agent Tools / External Integrations     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    API GATEWAY (FastAPI)                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Endpoints: /rag /analytics /export /agent /health /ml  │  │
│  │  Middleware: CORS, Auth, Logging, Telemetry             │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      CORE SERVICES LAYER                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────┐  ┌──────────────────────────────┐   │
│  │  INGESTION SERVICE   │  │   RAG RETRIEVAL SERVICE      │   │
│  ├──────────────────────┤  ├──────────────────────────────┤   │
│  │ • Multi-format       │  │ • Semantic Search            │   │
│  │   (PDF/CSV/TXT/MD)   │  │ • Hybrid Retrieval           │   │
│  │ • Chunking Strategy  │  │ • Reranking                  │   │
│  │ • Metadata Extract   │  │ • Confidence Scoring         │   │
│  │ • Duplicate Policy   │  │ • Graceful Degradation       │   │
│  └──────────────────────┘  └──────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────┐  ┌──────────────────────────────┐   │
│  │  ANALYTICS ENGINE    │  │  SUMMARIZATION SERVICE       │   │
│  ├──────────────────────┤  ├──────────────────────────────┤   │
│  │ • CSV Insights       │  │ • Document Summarization     │   │
│  │ • Statistical Profil │  │ • Key Points Extraction      │   │
│  │ • LLM Narrative Mode │  │ • Cross-File Insights        │   │
│  │ • Cache Management   │  │ • Semantic Clustering        │   │
│  └──────────────────────┘  └──────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────┐  ┌──────────────────────────────┐   │
│  │  EXPORT SERVICE      │  │  AGENT ORCHESTRATION         │   │
│  ├──────────────────────┤  ├──────────────────────────────┤   │
│  │ • Markdown Export    │  │ • Multi-Tool Execution       │   │
│  │ • PDF Generation     │  │ • Context Management         │   │
│  │ • Template Rendering │  │ • Iterative Reasoning        │   │
│  │ • Batch Processing   │  │ • Function Calling           │   │
│  └──────────────────────┘  └──────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────┐  ┌──────────────────────────────┐   │
│  │  ML PREDICTION       │  │  OBSERVABILITY LAYER         │   │
│  ├──────────────────────┤  ├──────────────────────────────┤   │
│  │ • Model Management   │  │ • Telemetry Tracking         │   │
│  │ • Feature Pipeline   │  │ • Latency Monitoring         │   │
│  │ • Cache & Fallback   │  │ • Graceful Degradation       │   │
│  │ • Batch Prediction   │  │ • Health Checks              │   │
│  └──────────────────────┘  └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      DATA PERSISTENCE LAYER                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────┐  ┌────────────────────────────┐  │
│  │   PostgreSQL Database   │  │   Vector Store (Chroma)    │  │
│  ├─────────────────────────┤  ├────────────────────────────┤  │
│  │ • Document Registry     │  │ • Embeddings Storage       │  │
│  │ • Metadata & Telemetry  │  │ • Similarity Search        │  │
│  │ • Ingestion Events      │  │ • Collection Management    │  │
│  │ • CSV Cache             │  │ • Filters & Metadata       │  │
│  │ • Chunk Tracking        │  │ • Persistent Storage       │  │
│  └─────────────────────────┘  └────────────────────────────┘  │
│                                                                  │
│  ┌─────────────────────────┐  ┌────────────────────────────┐  │
│  │    Redis (Optional)     │  │   File System Storage      │  │
│  ├─────────────────────────┤  ├────────────────────────────┤  │
│  │ • Cache Layer           │  │ • Uploaded Documents       │  │
│  │ • Celery Queue          │  │ • ML Model Artifacts       │  │
│  │ • Session Management    │  │ • Export Generation        │  │
│  └─────────────────────────┘  └────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. API Gateway (FastAPI)

**Purpose**: Central entry point for all client requests with middleware stack

**Key Features**:
- RESTful API endpoints with OpenAPI documentation
- Request validation with Pydantic models
- CORS handling for cross-origin requests
- Telemetry injection and tracking
- Error handling with graceful degradation

**Endpoints**:
- `/rag/*` - Document ingestion, retrieval, Q&A
- `/analytics/csv/*` - CSV insights and analytics
- `/export/*` - Document export (Markdown/PDF)
- `/agent/*` - Agent orchestration and tools
- `/ml/*` - ML predictions
- `/health` - System health checks

### 2. Ingestion Service

**Purpose**: Multi-format document processing with metadata extraction

**Pipeline Flow**:
```
Upload → Validation → Duplicate Check → Parse → Normalize → 
Chunk → Embed → Store (Vector + DB) → Index
```

**Supported Formats**:
- PDF (with OCR support)
- CSV/Excel (table processing)
- TXT, Markdown, DOCX
- Custom parsers extensible

**Features**:
- Configurable chunking strategies (fixed-size, semantic)
- Duplicate detection with hash-based deduplication
- Exists policies: skip / overwrite / version_as_new
- Metadata enrichment and tagging
- Graceful handling of partial failures

### 3. RAG Retrieval Service

**Purpose**: Intelligent document retrieval with hybrid search

**Retrieval Strategy**:
```
Query → Embedding → Semantic Search → Reranking → 
Confidence Filtering → Context Assembly → Response
```

**Features**:
- Semantic search via vector similarity
- Hybrid search (semantic + keyword + metadata filters)
- Confidence-based routing (high/medium/low confidence paths)
- Weak signal detection and handling
- Fallback to extractive methods
- Citation tracking with source attribution

### 4. Analytics Engine

**Purpose**: CSV data profiling and LLM-powered insights

**Capabilities**:
- Descriptive statistics (mean, median, std dev, quartiles)
- Categorical distribution analysis
- Data quality assessment (nulls, duplicates, outliers)
- Correlation analysis
- LLM narrative insights (optional mode)
- Intelligent caching with cache invalidation

**Cache Strategy**:
- Deterministic cache keys (document_id + config_hash)
- Cache hit/miss telemetry
- Small dataset skip logic (<10 rows)
- Graceful degradation on cache failures

### 5. Summarization Service

**Purpose**: Document summarization and cross-file insights

**Features**:
- Single document summarization
- Cross-file semantic clustering
- Key points extraction
- Topic identification
- Multi-document synthesis
- Confidence-scored outputs

### 6. Export Service

**Purpose**: Multi-format document generation

**Outputs**:
- Markdown (structured reports)
- PDF (rendered documents)
- JSON (structured data)
- Custom templates

### 7. Agent Orchestration

**Purpose**: Multi-step reasoning with tool execution

**Architecture**:
```
User Query → Planning → Tool Selection → Execution → 
Result Synthesis → Iterative Refinement → Final Answer
```

**Available Tools**:
- `ask_document` - RAG retrieval
- `summarize_document` - Summarization
- `predict_ml` - ML predictions
- Extensible tool registry

### 8. ML Prediction Service

**Purpose**: Machine learning model serving

**Features**:
- Model artifact management
- Feature pipeline
- Batch and single predictions
- Cache-aware inference
- Fallback handling

### 9. Observability Layer

**Purpose**: Comprehensive system monitoring and telemetry

**Tracked Metrics**:
- Latency (per component: retrieval, LLM, embedding)
- Routing decisions (confidence-based, fallback triggers)
- Cache behavior (hit/miss rates)
- Degradation levels (none, mild, degraded, fallback, failed)
- Error rates and types
- Resource utilization

**Graceful Degradation Levels**:
1. **None** - Full functionality
2. **Mild** - Minor quality reduction (low confidence)
3. **Degraded** - Reduced functionality (partial retrieval)
4. **Fallback** - Alternative method (extractive vs generative)
5. **Failed** - Operation failed with error message

## Data Flow Examples

### Example 1: Document Ingestion

```
1. Client uploads PDF → /rag/ingest-file
2. Validation: file size, format, checksum
3. Duplicate check: query PostgreSQL by hash
4. Parse: extract text, metadata, tables
5. Chunk: split into 200-char chunks with 50-char overlap
6. Embed: generate 384-dim vectors (all-MiniLM-L6-v2)
7. Store:
   - Chunks + embeddings → Chroma
   - Document metadata → PostgreSQL
   - File → File system
8. Return: document_id, chunk_count, status
```

### Example 2: RAG Query

```
1. Client sends question → /rag/answer
2. Embed query → vector (384-dim)
3. Semantic search → Chroma (top_k=5)
4. Rerank results by relevance
5. Confidence check:
   - High (>0.7): Full LLM generation
   - Medium (0.3-0.7): Guided generation
   - Low (<0.3): Extractive fallback
6. Generate answer with LLM
7. Track citations from chunks
8. Return: answer + citations + telemetry
```

### Example 3: CSV Analytics

```
1. Client requests insights → /analytics/csv/{doc_id}
2. Cache lookup: check if (doc_id + config) cached
3. If cache MISS:
   - Load CSV from file system
   - Compute statistics (pandas/numpy)
   - Generate LLM insights (optional)
   - Cache results → PostgreSQL
4. If cache HIT: return cached results
5. Return: summary + column_profiles + insights + meta
```

## Technology Stack

### Core Framework
- **FastAPI** - Async API framework
- **Pydantic** - Data validation
- **Uvicorn** - ASGI server

### Data Storage
- **PostgreSQL** - Document registry, metadata, cache
- **ChromaDB** - Vector embeddings and similarity search
- **Redis** (optional) - Caching and task queue
- **File System** - Document uploads and artifacts

### ML & Embeddings
- **Sentence Transformers** - Embedding generation (all-MiniLM-L6-v2)
- **Scikit-learn** - ML models and feature engineering
- **Pandas/NumPy** - Data processing and analytics

### Document Processing
- **PyPDF2 / pdfplumber** - PDF parsing
- **python-docx** - DOCX processing
- **Markdown** - Markdown parsing

### LLM Integration
- **OpenAI / Google Gemini** - Generative AI capabilities
- **LangChain** (optional) - LLM orchestration

### Observability
- **Custom Telemetry** - Latency, routing, cache tracking
- **Logging** - Structured logging with context
- **Health Checks** - Database, vector store, model availability

## Deployment Architecture

### Development
```
localhost:8000 (FastAPI)
localhost:5432 (PostgreSQL)
./data/vector_store (Chroma)
```

### Production
```
Load Balancer → FastAPI Instances (horizontal scaling)
                ↓
        PostgreSQL (managed service)
        ChromaDB (persistent volume)
        Redis (cache cluster)
        S3/Cloud Storage (file uploads)
```

## Security Considerations

1. **Input Validation**: All inputs validated with Pydantic
2. **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
3. **File Upload Safety**: File size limits, format validation, virus scanning
4. **API Authentication**: JWT tokens (not yet implemented - TODO)
5. **Rate Limiting**: Per-endpoint rate limits (TODO)
6. **Environment Secrets**: All credentials in `.env` (not committed)

## Performance Optimization

1. **Async I/O**: All database and network calls are async
2. **Connection Pooling**: PostgreSQL connection pool (min=5, max=20)
3. **Embedding Cache**: Reuse embeddings for identical queries
4. **CSV Cache**: Cache analytics results to avoid recomputation
5. **Batch Processing**: Chunk embedding in batches
6. **Lazy Loading**: Load large objects on-demand

## Graceful Degradation Strategy

The platform implements comprehensive graceful degradation:

```
Level 1: Optimal Path
  → High confidence retrieval + LLM generation

Level 2: Degraded Path  
  → Medium confidence retrieval + guided generation

Level 3: Fallback Path
  → Low confidence retrieval + extractive summary

Level 4: Minimal Path
  → No retrieval + generic response with error message

Level 5: Failed
  → Service unavailable with retry guidance
```

## Extensibility Points

1. **Custom Parsers**: Add new file format parsers
2. **Embedding Models**: Swap embedding models (BERT, GPT, etc.)
3. **LLM Providers**: Support multiple LLM backends
4. **Agent Tools**: Register new tools for agent orchestration
5. **Export Formats**: Add custom export templates
6. **Analytics Metrics**: Extend CSV analytics with domain-specific metrics

## Future Enhancements

1. **Multi-tenancy**: Workspace isolation and user management
2. **Advanced Search**: Filters, facets, date ranges
3. **Real-time Indexing**: Streaming ingestion pipeline
4. **Vector Index Optimization**: HNSW, IVF for faster retrieval
5. **Fine-tuned Models**: Domain-specific embedding and LLM models
6. **Webhooks**: Event-driven integrations
7. **API Versioning**: /v1, /v2 for backward compatibility
8. **Monitoring Dashboard**: Real-time metrics visualization

---

**Architecture Version**: 1.0  
**Last Updated**: January 5, 2026  
**Maintained By**: Enterprise RAG Team
