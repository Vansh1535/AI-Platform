"""
Generate Enterprise RAG Platform Architecture Diagram
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.lines as mlines

# Set up the figure
fig, ax = plt.subplots(figsize=(16, 12))
ax.set_xlim(0, 16)
ax.set_ylim(0, 12)
ax.axis('off')

# Colors
client_color = '#E8F4F8'
api_color = '#B3D9FF'
service_color = '#FFE6CC'
data_color = '#D5E8D4'
border_color = '#333333'

def draw_box(ax, x, y, width, height, text, color, fontsize=10, fontweight='normal'):
    """Draw a rounded rectangle with text"""
    box = FancyBboxPatch(
        (x, y), width, height,
        boxstyle="round,pad=0.05",
        linewidth=2,
        edgecolor=border_color,
        facecolor=color
    )
    ax.add_patch(box)
    ax.text(
        x + width/2, y + height/2, text,
        ha='center', va='center',
        fontsize=fontsize, fontweight=fontweight,
        wrap=True
    )

def draw_arrow(ax, x1, y1, x2, y2):
    """Draw an arrow between two points"""
    arrow = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle='->,head_width=0.3,head_length=0.3',
        linewidth=2,
        color='#666666'
    )
    ax.add_patch(arrow)

# Title
ax.text(8, 11.5, 'Enterprise RAG Platform - System Architecture',
        ha='center', va='center', fontsize=18, fontweight='bold')

# Layer 1: Client Layer
draw_box(ax, 1, 10.5, 14, 0.8, 
         'CLIENT LAYER\nWeb UI / API Clients / Agent Tools / External Integrations',
         client_color, fontsize=10, fontweight='bold')

# Layer 2: API Gateway
draw_box(ax, 1, 9, 14, 1.2,
         'API GATEWAY (FastAPI)\nEndpoints: /rag /analytics /export /agent /ml /health\nMiddleware: CORS, Auth, Logging, Telemetry',
         api_color, fontsize=10, fontweight='bold')

# Arrows from Client to API
draw_arrow(ax, 8, 10.5, 8, 10.2)

# Layer 3: Core Services (2 rows of 3 boxes each)
services = [
    # Row 1
    (1, 7, 4.3, 1.5, 'INGESTION SERVICE\n• Multi-format parsing\n• Chunking & embedding\n• Duplicate detection\n• Metadata extraction'),
    (5.5, 7, 4.3, 1.5, 'RAG RETRIEVAL SERVICE\n• Semantic search\n• Hybrid retrieval\n• Confidence scoring\n• Graceful degradation'),
    (10.2, 7, 4.3, 1.5, 'ANALYTICS ENGINE\n• CSV insights\n• Statistical profiling\n• LLM narrative mode\n• Cache management'),
    
    # Row 2
    (1, 5, 4.3, 1.5, 'SUMMARIZATION\n• Document summary\n• Key points extraction\n• Cross-file insights\n• Semantic clustering'),
    (5.5, 5, 4.3, 1.5, 'EXPORT SERVICE\n• Markdown export\n• PDF generation\n• Template rendering\n• Batch processing'),
    (10.2, 5, 4.3, 1.5, 'AGENT ORCHESTRATION\n• Multi-tool execution\n• Context management\n• Iterative reasoning\n• Function calling'),
]

for x, y, w, h, text in services:
    draw_box(ax, x, y, w, h, text, service_color, fontsize=8.5)

# Additional services row
draw_box(ax, 1, 3.2, 4.3, 1.5, 
         'ML PREDICTION\n• Model management\n• Feature pipeline\n• Cache & fallback\n• Batch prediction',
         service_color, fontsize=8.5)
draw_box(ax, 5.5, 3.2, 4.3, 1.5,
         'OBSERVABILITY LAYER\n• Telemetry tracking\n• Latency monitoring\n• Graceful degradation\n• Health checks',
         service_color, fontsize=8.5)

# Arrows from API to Services
draw_arrow(ax, 3, 9, 3, 8.5)
draw_arrow(ax, 8, 9, 7.5, 8.5)
draw_arrow(ax, 13, 9, 12.5, 8.5)

# Layer 4: Data Persistence
persistence = [
    (1, 0.5, 3.3, 2.3, 'PostgreSQL Database\n• Document registry\n• Metadata & telemetry\n• Ingestion events\n• CSV cache\n• Chunk tracking'),
    (4.5, 0.5, 3.3, 2.3, 'Vector Store (Chroma)\n• Embeddings storage\n• Similarity search\n• Collection management\n• Filters & metadata\n• Persistent storage'),
    (8, 0.5, 3.3, 2.3, 'Redis (Optional)\n• Cache layer\n• Celery queue\n• Session management\n• Rate limiting'),
    (11.5, 0.5, 3.3, 2.3, 'File System Storage\n• Uploaded documents\n• ML model artifacts\n• Export generation\n• Logs & backups'),
]

for x, y, w, h, text in persistence:
    draw_box(ax, x, y, w, h, text, data_color, fontsize=8)

# Arrows from Services to Data layer
draw_arrow(ax, 3, 3.2, 2.5, 2.8)
draw_arrow(ax, 7.5, 3.2, 6, 2.8)
draw_arrow(ax, 12.5, 3.2, 13, 2.8)

# Add legend
legend_elements = [
    mlines.Line2D([0], [0], marker='s', color='w', markerfacecolor=client_color, 
                  markersize=10, label='Client Layer', markeredgecolor=border_color, markeredgewidth=2),
    mlines.Line2D([0], [0], marker='s', color='w', markerfacecolor=api_color,
                  markersize=10, label='API Gateway', markeredgecolor=border_color, markeredgewidth=2),
    mlines.Line2D([0], [0], marker='s', color='w', markerfacecolor=service_color,
                  markersize=10, label='Core Services', markeredgecolor=border_color, markeredgewidth=2),
    mlines.Line2D([0], [0], marker='s', color='w', markerfacecolor=data_color,
                  markersize=10, label='Data Persistence', markeredgecolor=border_color, markeredgewidth=2),
]
ax.legend(handles=legend_elements, loc='lower right', fontsize=9)

# Add version info
ax.text(0.5, 0.1, 'Version 1.0 | January 2026', 
        fontsize=8, style='italic', color='#666666')

plt.tight_layout()
plt.savefig('docs/architecture/architecture_diagram.png', dpi=300, bbox_inches='tight', 
            facecolor='white', edgecolor='none')
print("✅ Architecture diagram generated: docs/architecture/architecture_diagram.png")
