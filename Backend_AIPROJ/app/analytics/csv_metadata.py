"""
CSV Metadata Storage Service

Handles CSV-specific metadata storage in PostgreSQL to avoid ChromaDB limitations.
ChromaDB doesn't support complex metadata types (lists, nested dicts), so we store
CSV schema information, column statistics, and sample data in PostgreSQL.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import json
from app.core.db.postgres import get_session
from app.core.db.models import Document
from app.core.logging import setup_logger

logger = setup_logger()


async def save_csv_metadata_to_db(
    document_id: str,
    schema: Dict[str, str],
    column_stats: Dict[str, Any],
    row_count: int,
    column_count: int,
    sample_rows: List[Dict[str, Any]] = None,
    data_quality: Dict[str, Any] = None
) -> bool:
    """
    Save CSV-specific metadata to PostgreSQL document_metadata JSON field.
    
    Args:
        document_id: Document ID from ingestion
        schema: Column name to data type mapping
        column_stats: Statistical information per column
        row_count: Number of rows in CSV
        column_count: Number of columns in CSV
        sample_rows: Optional sample rows (first 5-10 rows)
        data_quality: Optional data quality metrics (nulls, duplicates, etc.)
    
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        async with get_session() as session:
            # Find document by ID
            result = await session.execute(
                "SELECT id, document_metadata FROM documents WHERE id = :doc_id",
                {"doc_id": document_id}
            )
            row = result.fetchone()
            
            if not row:
                logger.warning(f"Document {document_id} not found for CSV metadata save")
                return False
            
            # Get existing metadata or create new
            existing_metadata = row[1] if row[1] else {}
            
            # Build CSV-specific metadata structure
            csv_metadata = {
                "csv_schema": schema,
                "csv_column_stats": column_stats,
                "csv_row_count": row_count,
                "csv_column_count": column_count,
                "csv_sample_rows": sample_rows[:5] if sample_rows else [],  # Limit to 5 rows
                "csv_data_quality": data_quality or {},
                "csv_metadata_stored_at": datetime.utcnow().isoformat()
            }
            
            # Merge with existing metadata
            existing_metadata.update(csv_metadata)
            
            # Update document
            await session.execute(
                "UPDATE documents SET document_metadata = :metadata, updated_at = :now WHERE id = :doc_id",
                {
                    "metadata": json.dumps(existing_metadata),
                    "now": datetime.utcnow(),
                    "doc_id": document_id
                }
            )
            await session.commit()
            
            logger.info(
                f"CSV metadata saved for document {document_id}: "
                f"{row_count} rows, {column_count} columns"
            )
            return True
            
    except Exception as e:
        logger.error(f"Failed to save CSV metadata for {document_id}: {str(e)}")
        return False


async def load_csv_metadata_from_db(document_id: str) -> Optional[Dict[str, Any]]:
    """
    Load CSV-specific metadata from PostgreSQL.
    
    Args:
        document_id: Document ID
    
    Returns:
        Dictionary with CSV metadata or None if not found
    """
    try:
        async with get_session() as session:
            result = await session.execute(
                "SELECT document_metadata FROM documents WHERE id = :doc_id",
                {"doc_id": document_id}
            )
            row = result.fetchone()
            
            if not row or not row[0]:
                logger.info(f"No metadata found for document {document_id}")
                return None
            
            metadata = row[0]
            
            # Extract CSV-specific fields
            csv_metadata = {
                "schema": metadata.get("csv_schema"),
                "column_stats": metadata.get("csv_column_stats"),
                "row_count": metadata.get("csv_row_count"),
                "column_count": metadata.get("csv_column_count"),
                "sample_rows": metadata.get("csv_sample_rows", []),
                "data_quality": metadata.get("csv_data_quality", {}),
                "stored_at": metadata.get("csv_metadata_stored_at")
            }
            
            # Return None if no CSV metadata exists
            if not csv_metadata.get("schema"):
                return None
            
            logger.info(f"Loaded CSV metadata for document {document_id}")
            return csv_metadata
            
    except Exception as e:
        logger.error(f"Failed to load CSV metadata for {document_id}: {str(e)}")
        return None


def extract_csv_metadata_for_storage(df) -> Dict[str, Any]:
    """
    Extract CSV metadata from pandas DataFrame for PostgreSQL storage.
    
    Args:
        df: pandas DataFrame
    
    Returns:
        Dictionary with schema, stats, and quality metrics
    """
    import pandas as pd
    
    # Extract schema (column names and types)
    schema = {col: str(dtype) for col, dtype in df.dtypes.items()}
    
    # Extract column statistics
    column_stats = {}
    for col in df.columns:
        stats = {
            "type": str(df[col].dtype),
            "null_count": int(df[col].isnull().sum()),
            "unique_count": int(df[col].nunique())
        }
        
        # Add numeric stats if applicable
        if pd.api.types.is_numeric_dtype(df[col]):
            stats.update({
                "mean": float(df[col].mean()) if not df[col].isnull().all() else None,
                "std": float(df[col].std()) if not df[col].isnull().all() else None,
                "min": float(df[col].min()) if not df[col].isnull().all() else None,
                "max": float(df[col].max()) if not df[col].isnull().all() else None
            })
        
        column_stats[col] = stats
    
    # Extract data quality metrics
    data_quality = {
        "total_nulls": int(df.isnull().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "completeness_ratio": float(1 - (df.isnull().sum().sum() / (len(df) * len(df.columns))))
    }
    
    # Extract sample rows (first 5)
    sample_rows = df.head(5).to_dict('records')
    # Convert numpy types to native Python types
    for row in sample_rows:
        for key, value in row.items():
            if pd.isna(value):
                row[key] = None
            elif hasattr(value, 'item'):  # numpy types
                row[key] = value.item()
    
    return {
        "schema": schema,
        "column_stats": column_stats,
        "row_count": len(df),
        "column_count": len(df.columns),
        "sample_rows": sample_rows,
        "data_quality": data_quality
    }
