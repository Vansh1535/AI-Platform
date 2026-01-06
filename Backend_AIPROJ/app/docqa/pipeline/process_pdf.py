import pdfplumber
from pathlib import Path
from typing import List, Dict
from app.core.logging import setup_logger

logger = setup_logger("INFO")


def process_pdf(file_path: str) -> List[Dict[str, any]]:
    """
    Extract text from a PDF file page by page.
    
    Args:
        file_path: Path to the PDF file
    
    Returns:
        List of dictionaries with page number and text content
        
    Raises:
        FileNotFoundError: If the PDF file doesn't exist
        Exception: If PDF processing fails
    """
    pdf_path = Path(file_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    logger.info(f"Processing PDF: {pdf_path.name}")
    
    pages_data = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            logger.info(f"PDF has {total_pages} pages")
            
            for page_num, page in enumerate(pdf.pages, start=1):
                # Extract text from the page
                text = page.extract_text()
                
                if text and text.strip():
                    pages_data.append({
                        "page": page_num,
                        "text": text.strip()
                    })
                    logger.debug(f"Extracted text from page {page_num}")
                else:
                    logger.warning(f"No text found on page {page_num}")
        
        logger.info(f"Successfully extracted text from {len(pages_data)} pages")
        return pages_data
        
    except Exception as e:
        logger.error(f"Failed to process PDF: {str(e)}")
        raise Exception(f"PDF processing failed: {str(e)}")
