# Backend API Capabilities - Ground Truth

**Last Audited:** January 7, 2026
**Purpose:** Define what the backend can ACTUALLY do (no mocking allowed in frontend)

---

## ✅ WORKING Endpoints (Use These)

### 1. Document Management (`/rag/docs`)
```
✅ GET  /rag/docs/list                      # List all documents
✅ GET  /rag/docs/{id}/meta                 # Get document metadata
✅ GET  /rag/docs/{id}/preview              # Preview chunks
✅ GET  /rag/docs/checksum/{hash}           # Check duplicate
✅ GET  /rag/docs/health                    # Ingestion health
```

### 2. Document Ingestion (`/rag`)
```
✅ POST /rag/ingest                         # Ingest raw text
✅ POST /rag/ingest-pdf                     # Async PDF ingestion
✅ POST /rag/ingest-file                    # Multi-format upload (PDF, CSV, TXT, DOCX, MD)
✅ GET  /rag/ingest-status/{job_id}         # Check async job status
✅ GET  /rag/supported-formats              # Get supported formats
```

### 3. RAG Search & Q&A (`/rag`)
```
✅ POST /rag/query                          # Semantic search
✅ POST /rag/answer                         # Question answering with citations
✅ POST /rag/summarize                      # Document summarization
```

### 4. Analytics (`/rag`)
```
✅ GET  /rag/analytics/csv/{doc_id}         # CSV insights (stats + LLM analysis)
✅ POST /rag/rag/insights/aggregate         # Aggregate insights
✅ POST /rag/insights/cross-file            # Cross-document insights
✅ GET  /rag/insights/cross-file            # Get cached cross-file insights
```

### 5. Agent Orchestration (`/agent`)
```
✅ POST /agent/run                          # Execute agent task
✅ GET  /agent/tools                        # List available tools
```

### 6. Export (`/export`)
```
✅ POST /export/report                      # Generate report (markdown/PDF)
✅ GET  /export/capabilities                # Export capabilities
```

### 7. ML (`/ml`)
```
✅ POST /ml/predict                         # Make prediction
```

### 8. Health Check
```
✅ GET  /health                             # Overall health
```

---

## ❌ MISSING Endpoints (Don't Mock These)

### Document Management
```
❌ DELETE /rag/docs/{id}                    # Cannot delete documents
❌ PUT    /rag/docs/{id}                    # Cannot update metadata
❌ GET    /rag/docs/stats                   # No aggregated stats endpoint
```

### ML Training
```
❌ POST   /ml/train                         # Cannot train models via API
❌ GET    /ml/models                        # Cannot list trained models
❌ GET    /ml/training/{job_id}/status      # No training status
```

### Real-Time
```
❌ WebSocket /ws                            # No WebSocket support
❌ GET  /events                             # No Server-Sent Events
```

### Authentication
```
❌ POST /auth/login                         # No authentication
❌ POST /auth/register                      # No user management
❌ GET  /auth/me                            # No current user endpoint
```

---

## 📊 Backend Data Models

### Document
```python
{
  "id": "uuid",
  "filename": "document.pdf",
  "format": "pdf",
  "status": "completed" | "processing" | "failed",
  "chunks": 42,
  "upload_timestamp": "ISO8601",
  "source": "user_upload",
  "checksum": "sha256_hash"
}
```

### Search Result
```python
{
  "chunk": "text content",
  "score": 0.85,  # Float 0-1
  "metadata": {
    "filename": "doc.pdf",
    "chunk_index": 5,
    "format": "pdf",
    "document_id": "uuid"
  }
}
```

### Answer Response
```python
{
  "answer": "Generated answer text",
  "citations": [
    {
      "chunk": "source text",
      "score": 0.9,
      "filename": "doc.pdf",
      "metadata": {...}
    }
  ],
  "used_chunks": 3,
  "metadata": {
    "provider": "gemini" | "openai" | "ollama",
    "latency_ms_retrieval": 123,
    "latency_ms_llm": 456,
    "cache_hit": true
  }
}
```

### CSV Insights
```python
{
  "basic_stats": {
    "row_count": 1000,
    "column_count": 10,
    "file_size_mb": 2.5,
    "null_count": 15,
    "duplicate_rows": 3
  },
  "column_stats": [...],  # Array of column statistics
  "quality": {
    "missing_values": {"col1": 5},
    "completeness_score": 0.95
  },
  "correlations": [...],  # Correlation matrix
  "llm_insights": {
    "summary": "Overall analysis",
    "key_findings": ["finding1", "finding2"],
    "recommendations": ["rec1", "rec2"]
  }
}
```

---

## 🎯 Frontend Feature Matrix

| Feature | Backend Support | Frontend Action |
|---------|----------------|-----------------|
| **Document Upload** | ✅ Full | Use `/rag/ingest-file` |
| **Document List** | ✅ Full | Use `/rag/docs/list` |
| **Document Preview** | ✅ Full | Use `/rag/docs/{id}/preview` |
| **Document Delete** | ❌ None | **Hide delete button** |
| **Semantic Search** | ✅ Full | Use `/rag/query` |
| **Q&A Chat** | ✅ Full | Use `/rag/answer` |
| **CSV Analytics** | ✅ Full | Use `/rag/analytics/csv/{id}` |
| **Summarization** | ✅ Full | Use `/rag/summarize` |
| **Export Reports** | ✅ Full | Use `/export/report` |
| **Agent Tasks** | ✅ Full | Use `/agent/run` |
| **ML Predictions** | ✅ Partial | Use `/ml/predict` (pre-trained only) |
| **ML Training** | ❌ None | **Hide training UI** |
| **Real-time Updates** | ❌ None | **Use polling with refetchInterval** |
| **User Auth** | ❌ None | **Skip role-based access (no admin mode)** |

---

## 🚀 Refactoring Strategy

### ✅ DO (Backend Supports This)
1. **Document Intelligence Hub** (merge docs + RAG + analytics + export)
   - Upload → List → Preview → Search → Q&A → Analyze (CSV) → Export
2. **Agent Workspace** (use existing tools)
   - Run tasks with real backend execution
3. **ML Predictions** (simple interface)
   - Only predictions, hide training
4. **Polling for Upload Status**
   - Use `refetchInterval` in React Query

### ❌ DON'T (Backend Doesn't Support)
1. ~~WebSocket live updates~~ → Use polling instead
2. ~~ML model training UI~~ → Hide completely
3. ~~Admin dashboard~~ → Everyone sees same UI
4. ~~Delete documents~~ → No delete button
5. ~~User authentication~~ → Skip for now

---

## 📝 Implementation Checklist

### Phase 1: Fix Broken Connections (CRITICAL)
- [ ] Verify all API endpoints match backend paths
- [ ] Fix frontend API client to use correct URLs
- [ ] Test each endpoint with real backend
- [ ] Remove any mock data

### Phase 2: Restructure Pages (Keep 100% Real)
- [ ] Merge: Documents + RAG + CSV Analytics + Summarize + Export → `/documents`
- [ ] Keep: ML predictions only (no training)
- [ ] Keep: Agent execution
- [ ] Remove: Health dashboard (or make read-only)

### Phase 3: Add Polling (Simulate Real-time)
- [ ] Poll document list every 5s during upload
- [ ] Poll job status for async PDF ingestion
- [ ] Show upload progress based on status endpoint

### Phase 4: UI Enhancements (No Backend Changes)
- [ ] Better loading states
- [ ] Progress bars (based on polling)
- [ ] Toast notifications
- [ ] Skeleton loaders
- [ ] Error boundaries

---

## 🔍 Testing Commands

```bash
# Test all working endpoints
curl http://localhost:8000/health
curl http://localhost:8000/rag/docs/list
curl http://localhost:8000/rag/supported-formats
curl http://localhost:8000/agent/tools
curl http://localhost:8000/export/capabilities
curl http://localhost:8000/rag/docs/health
```

---

**GOLDEN RULE:** If it's not in the "✅ WORKING Endpoints" section, DO NOT build UI for it.
