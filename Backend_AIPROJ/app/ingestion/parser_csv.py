"""
CSV parser - creates intelligent text projection for embeddings.
Does NOT dump raw CSV as text - generates schema summary and data description.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
import csv
from app.core.logging import setup_logger
from .dispatcher import ParsedDocument

logger = setup_logger()


def infer_column_types(rows: List[List[str]], headers: List[str]) -> Dict[str, str]:
    """
    Infer basic column types from sample data.
    
    Args:
        rows: Sample of data rows
        headers: Column headers
        
    Returns:
        Dictionary mapping column name to inferred type
    """
    column_types = {}
    
    for i, header in enumerate(headers):
        # Sample values from column
        sample_values = [row[i] for row in rows[:min(20, len(rows))] if i < len(row) and row[i].strip()]
        
        if not sample_values:
            column_types[header] = "empty"
            continue
        
        # Check if numeric
        try:
            [float(v.replace(',', '')) for v in sample_values]
            column_types[header] = "numeric"
            continue
        except ValueError:
            pass
        
        # Check if boolean-like
        unique_values = set(v.lower() for v in sample_values)
        if unique_values.issubset({'true', 'false', 'yes', 'no', '1', '0', 't', 'f', 'y', 'n'}):
            column_types[header] = "boolean"
            continue
        
        # Default to text
        column_types[header] = "text"
    
    return column_types


def create_csv_projection(
    headers: List[str],
    rows: List[List[str]],
    column_types: Dict[str, str],
    file_name: str
) -> str:
    """
    Create a text projection of CSV data for embeddings.
    Describes structure and content without dumping raw data.
    
    Args:
        headers: Column headers
        rows: All data rows
        column_types: Inferred column types
        file_name: Name of the CSV file
        
    Returns:
        Text summary suitable for embedding
    """
    lines = []
    
    # Header section
    lines.append(f"CSV Data Table: {file_name}")
    lines.append("=" * 60)
    lines.append("")
    
    # Schema description
    lines.append("Schema:")
    lines.append(f"- Total Columns: {len(headers)}")
    lines.append(f"- Total Rows: {len(rows)}")
    lines.append("")
    
    lines.append("Column Definitions:")
    for header in headers:
        col_type = column_types.get(header, "unknown")
        lines.append(f"  • {header} ({col_type})")
    lines.append("")
    
    # Sample data (first 3 rows)
    lines.append("Sample Data (first 3 rows):")
    sample_rows = rows[:3]
    for i, row in enumerate(sample_rows, 1):
        lines.append(f"  Row {i}:")
        for j, header in enumerate(headers):
            value = row[j] if j < len(row) else "N/A"
            if len(value) > 50:
                value = value[:47] + "..."
            lines.append(f"    {header}: {value}")
        lines.append("")
    
    # Statistical summary for numeric columns
    numeric_cols = [h for h, t in column_types.items() if t == "numeric"]
    if numeric_cols:
        lines.append("Numeric Column Summary:")
        for col_name in numeric_cols:
            col_idx = headers.index(col_name)
            values = []
            for row in rows:
                if col_idx < len(row):
                    try:
                        values.append(float(row[col_idx].replace(',', '')))
                    except ValueError:
                        pass
            
            if values:
                lines.append(f"  • {col_name}:")
                lines.append(f"    - Min: {min(values):.2f}")
                lines.append(f"    - Max: {max(values):.2f}")
                lines.append(f"    - Average: {sum(values)/len(values):.2f}")
        lines.append("")
    
    # Unique values for categorical columns (if reasonable count)
    text_cols = [h for h, t in column_types.items() if t == "text"]
    for col_name in text_cols[:3]:  # Limit to first 3 text columns
        col_idx = headers.index(col_name)
        unique_values = set()
        for row in rows:
            if col_idx < len(row) and row[col_idx].strip():
                unique_values.add(row[col_idx].strip())
        
        if 2 <= len(unique_values) <= 20:  # Only show if reasonable count
            lines.append(f"Unique values in '{col_name}':")
            for value in sorted(unique_values)[:10]:  # Show max 10
                lines.append(f"  - {value}")
            if len(unique_values) > 10:
                lines.append(f"  ... and {len(unique_values) - 10} more")
            lines.append("")
    
    return '\n'.join(lines)


def parse_csv(file_path: str, source: Optional[str] = None) -> ParsedDocument:
    """
    Parse CSV file and create intelligent text projection.
    
    Args:
        file_path: Path to CSV file
        source: Optional source identifier
        
    Returns:
        ParsedDocument with text projection and table metadata
        
    Raises:
        Exception: If CSV parsing fails
    """
    try:
        logger.info(f"Parsing CSV: {Path(file_path).name}")
        
        path = Path(file_path)
        
        # Read CSV with automatic delimiter detection
        with open(file_path, 'r', encoding='utf-8', newline='') as f:
            # Detect delimiter
            sample = f.read(4096)
            f.seek(0)
            
            sniffer = csv.Sniffer()
            try:
                dialect = sniffer.sniff(sample)
                delimiter = dialect.delimiter
            except csv.Error:
                delimiter = ','  # Default to comma
            
            logger.info(f"CSV delimiter detected: '{delimiter}'")
            
            # Read all rows
            reader = csv.reader(f, delimiter=delimiter)
            rows = list(reader)
        
        if not rows:
            raise ValueError("CSV file is empty")
        
        # Extract headers (first row)
        headers = rows[0]
        data_rows = rows[1:]
        
        if not data_rows:
            raise ValueError("CSV file contains only headers, no data")
        
        # Infer column types
        column_types = infer_column_types(data_rows, headers)
        
        # Create text projection
        text_projection = create_csv_projection(
            headers=headers,
            rows=data_rows,
            column_types=column_types,
            file_name=path.name
        )
        
        # Build metadata
        metadata = {
            "source": source or path.name,
            "file_name": path.name,
            "row_count": len(data_rows),
            "column_count": len(headers),
            "columns": headers,
            "column_types": column_types,
            "delimiter": delimiter
        }
        
        logger.info(
            f"CSV parsed successfully - {len(data_rows)} rows, "
            f"{len(headers)} columns, projection: {len(text_projection)} chars"
        )
        
        return ParsedDocument(
            text=text_projection,
            sections=None,  # CSV doesn't have natural sections
            source_type="table",
            format="csv",
            metadata=metadata
        )
        
    except Exception as e:
        logger.error(f"CSV parsing failed for {file_path}: {str(e)}")
        raise Exception(f"Failed to parse CSV: {str(e)}") from e
