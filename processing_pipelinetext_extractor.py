import pdfminer.high_level
import PyPDF2
from firebase_init import db
import logging
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TextExtractor:
    def __init__(self):
        self.db = db
    
    def extract_text(self, pdf_path: str) -> str:
        """Extract text from PDF using pdfminer, fallback to PyPDF2."""
        try:
            text = pdfminer.high_level.extract_text(pdf_path)
            if text and len(text.strip()) > 100:  # Assume sufficient text
                return text
        except Exception as e:
            logger.warning(f"pdfminer failed for {pdf_path}: {e}")
        
        # Fallback to PyPDF2
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                return text
        except Exception as e:
            logger.error(f"PyPDF2 also failed for {pdf_path}: {e}")
            return ""
    
    def process_queue(self):
        """Process all papers with status 'pdf_downloaded'."""
        queue_ref = self.db.collection("ingestion_queue")
        downloaded_papers = queue_ref.where("status", "==", "pdf_downloaded").stream()
        
        for paper in downloaded_papers:
            paper_data = paper.to_dict()
            paper_id = paper.id
            
            pdf_path = paper_data.get("pdf_local_path")
            if not pdf_path or not os.path.exists(pdf_path):
                logger.warning(f"PDF file not found for {paper_id}")
                paper.reference.update({
                    "status": "text_extraction_failed",
                    "updated_at": datetime.now()
                })
                continue
            
            text = self.extract_text(pdf_path)
            if text:
                # Save text to a new collection 'paper_texts'
                text_ref = self.db.collection("paper_texts").document(paper_id)
                text_ref.set({
                    "paper_id": paper_id,
                    "text": text,
                    "created_at": datetime.now()
                })
                
                paper.reference.update({
                    "status": "text_extracted",
                    "updated_at": datetime.now()
                })
                logger.info(f"Extracted text for {paper_id}")
            else:
                paper.reference.update({
                    "status": "text_extraction_failed",
                    "updated_at": datetime.now()
                })
                logger.error(f"Text extraction failed for {paper_id}")