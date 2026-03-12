import requests
from firebase_init import db
import logging
from datetime import datetime
import os
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFFetcher:
    def __init__(self, storage_path: str = "./pdfs"):
        self.db = db
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
    
    def fetch_pdf(self, paper_id: str, pdf_url: str) -> Optional[str]:
        """Fetch PDF and save locally. Returns local file path."""
        if not pdf_url:
            logger.warning(f"No PDF URL for paper {paper_id}")
            return None
        
        try:
            response = requests.get(pdf_url, timeout=10)
            response.raise_for_status()
            
            file_path = os.path.join(self.storage_path, f"{paper_id}.pdf")
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded PDF for {paper_id} to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to download PDF for {paper_id}: {e}")
            return None
    
    def process_queue(self):
        """Process all papers in ingestion_queue with status 'pending' and a PDF URL."""
        queue_ref = self.db.collection("ingestion_queue")
        pending_papers = queue_ref.where("status", "==", "pending").stream()
        
        for paper in pending_papers:
            paper_data = paper.to_dict()
            paper_id = paper.id
            
            # Check if PDF URL exists
            pdf_url = paper_data.get("pdf_url")
            if not pdf_url:
                logger.info(f"No PDF URL for {paper_id}, skipping.")
                continue
            
            # Download PDF
            local_path = self.fetch_pdf(paper_id, pdf_url)
            
            # Update status in Firestore
            if local_path:
                paper.reference.update({
                    "status": "pdf_downloaded",
                    "pdf_local_path": local_path,
                    "updated_at": datetime.now()
                })
            else:
                paper.reference.update({
                    "status": "pdf_failed",
                    "updated_at": datetime.now()
                })