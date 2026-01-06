from typing import List, Dict


def chunk_text_with_metadata(
    text: str, 
    page: int, 
    source: str,
    chunk_size: int = 200, 
    overlap: int = 50
) -> List[Dict[str, any]]:
    """
    Split text into overlapping chunks with metadata.
    
    Args:
        text: The text to chunk
        page: Page number where the text came from
        source: Source document identifier
        chunk_size: Size of each chunk in characters
        overlap: Number of overlapping characters between chunks
    
    Returns:
        List of chunks with metadata
    """
    chunks = []
    start = 0
    text_length = len(text)
    chunk_index = 0
    
    while start < text_length:
        end = start + chunk_size
        chunk_text = text[start:end].strip()
        
        if chunk_text:  # Only add non-empty chunks
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "page": page,
                    "source": source,
                    "chunk_index": chunk_index
                }
            })
            chunk_index += 1
        
        start += chunk_size - overlap
    
    return chunks


def chunk_pages(
    pages_data: List[Dict[str, any]], 
    source: str,
    chunk_size: int = 200,
    overlap: int = 50
) -> List[Dict[str, any]]:
    """
    Chunk multiple pages of text with metadata.
    
    Args:
        pages_data: List of page data with 'page' and 'text' keys
        source: Source document identifier
        chunk_size: Size of each chunk in characters
        overlap: Number of overlapping characters between chunks
    
    Returns:
        List of all chunks from all pages with metadata
    """
    all_chunks = []
    
    for page_data in pages_data:
        page_num = page_data["page"]
        page_text = page_data["text"]
        
        page_chunks = chunk_text_with_metadata(
            text=page_text,
            page=page_num,
            source=source,
            chunk_size=chunk_size,
            overlap=overlap
        )
        
        all_chunks.extend(page_chunks)
    
    return all_chunks
