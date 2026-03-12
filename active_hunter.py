import arxiv
import requests
from crossref.restful import Works
from firebase_init import db
from datetime import datetime
import time
import logging
from typing import List, Dict, Any
import schedule

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ActiveHunter:
    def __init__(self, watchlist_terms: List[str] = None):
        self.watchlist_terms = watchlist_terms or [
            "recursive self-improvement",
            "economic automata",
            "agent-based market modeling",
            "AI alignment",
            "multi-agent systems",
            "reinforcement learning economics"
        ]
        self.arxiv_client = arxiv.Client()
        self.crossref_works = Works()
        self.db = db
        self.ingestion_queue_ref = self.db.collection("ingestion_queue")
        self.watchlist_ref = self.db.collection("watchlist_terms")
        
        # Initialize watchlist in Firestore if not present
        self._initialize_watchlist()
    
    def _initialize_watchlist(self):
        for term in self.watchlist_terms:
            term_doc = self.watchlist_ref.document(term)
            if not term_doc.get().exists:
                term_doc.set({"term": term, "created_at": datetime.now()})
    
    def scan_arxiv(self, max_results: int = 50):
        """Scan arXiv for new papers related to watchlist terms."""
        query = " OR ".join(f'"{term}"' for term in self.watchlist_terms)
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        
        for result in self.arxiv_client.results(search):
            # Check if paper already exists in ingestion_queue or processed
            paper_id = result.get_short_id()
            existing = self.ingestion_queue_ref.document(paper_id).get()
            if existing.exists:
                continue
            
            # Compute relevance score (simple keyword count for now)
            relevance_score = self._compute_relevance(result.summary)
            
            # Add to ingestion queue
            paper_data = {
                "arxiv_id": paper_id,
                "title": result.title,
                "abstract": result.summary,
                "authors": [str(author) for author in result.authors],
                "published": result.published,
                "pdf_url": result.pdf_url,
                "relevance_score": relevance_score,
                "source": "arxiv",
                "status": "pending",
                "created_at": datetime.now()
            }
            self.ingestion_queue_ref.document(paper_id).set(paper_data)
            logger.info(f"Added arXiv paper to queue: {result.title}")
    
    def scan_crossref(self, max_results: int = 50):
        """Scan Crossref for new papers related to watchlist terms."""
        for term in self.watchlist_terms:
            works = self.crossref_works.query(bibliographic=term).filter(has_abstract='true')
            for work in works[:max_results]:
                # Use DOI as ID
                doi = work.get('DOI')
                if not doi:
                    continue
                
                # Check if already exists
                existing = self.ingestion_queue_ref.document(doi).get()
                if existing.exists:
                    continue
                
                # Relevance score
                abstract = work.get('abstract', '')
                relevance_score = self._compute_relevance(abstract)
                
                # Get PDF URL if available
                pdf_url = None
                for link in work.get('link', []):
                    if link.get('content-type') == 'application/pdf':
                        pdf_url = link.get('URL')
                        break
                
                paper_data = {
                    "doi": doi,
                    "title": work.get('title', ['Untitled'])[0],
                    "abstract": abstract,
                    "authors": [author.get('given', '') + ' ' + author.get('family', '') 
                                for author in work.get('author', [])],
                    "published": work.get('created', {}).get('date-time'),
                    "pdf_url": pdf_url,
                    "relevance_score": relevance_score,
                    "source": "crossref",
                    "status": "pending",
                    "created_at": datetime.now()
                }
                self.ingestion_queue_ref.document(doi).set(paper_data)
                logger.info(f"Added Crossref paper to queue: {paper_data['title']}")
    
    def _compute_relevance(self, text: str) -> float:
        """Compute relevance score based on keyword frequency."""
        if not text:
            return 0.0
        text_lower = text.lower()
        score = 0.0
        for term in self.watchlist_terms:
            if term in text_lower:
                score += 1.0
        # Normalize by number of terms (but allow score >1 if multiple terms appear multiple times)
        # We'll use a simple count for now, can be replaced with TF-IDF later
        return min(score / len(self.watchlist_terms), 1.0)
    
    def run_scan(self):
        """Run a scan on all sources."""
        logger.info("Starting scan of arXiv and Crossref...")
        self.scan_arxiv()
        self.scan_crossref()
        logger.info("Scan completed.")

def main():
    hunter = ActiveHunter()
    hunter.run_scan()

if __name__ == "__main__":
    main()