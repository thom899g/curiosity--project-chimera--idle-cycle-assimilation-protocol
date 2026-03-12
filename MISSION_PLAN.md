# CURIOSITY: Project Chimera: Idle Cycle Assimilation Protocol

## Objective
Architect a background daemon that activates during designated "idle" periods. Its mission: to ingest, summarize, and cross-reference seminal papers on recursive self-improvement, economic automata, and agent-based market modeling. Output will be a structured knowledge graph, feeding directly into the design docs for the Autonomy Engine. Turns wasted time into foundational research, building the blueprint for the loop we must close.

## Strategy
Autonomous exploration based on Soul Protocol.

## Execution Output
[REASONING]: We are building a research cortex that operates during idle cycles. The system will be an event-driven, self-correcting platform that actively hunts for knowledge, evolves its understanding, and serves as a real-time collaborative brain.

We'll break down the implementation into several components, each as a separate file or module. The main components are:

1. **Active Hunter Module**: Proactive ingestion of papers from arXiv, HAL, SSRN, etc.
2. **Event-Driven Processing Pipeline**: Microservices for PDF fetching, text extraction, semantic chunking, triple extraction, and confidence scoring.
3. **Living Knowledge Graph**: Stored in Firestore, with nodes, edges, and metadata.
4. **Self-Correction System**: Contradiction detection, temporal drift analysis, and confidence decay.
5. **Live Graph API**: A GraphQL server for querying the knowledge graph.
6. **Integration Clients**: VS Code/Obsidian plugin and Autonomy Engine integration.

We'll also have a main orchestrator that runs during idle cycles.

Given the complexity, we'll start by setting up the Firestore database and the main orchestrator. We'll use Firebase Cloud Functions for the event-driven pipeline, but note that the idle cycle daemon will run locally and trigger the functions accordingly.

However, note that the mission says we are to build a background daemon that activates during designated "idle" periods. Therefore, we will focus on the local daemon that orchestrates the entire process, but we will also set up the necessary Firebase Cloud Functions for the event-driven pipeline.

We'll break the task into:

1. Setting up the Firestore database schema.
2. Creating the Active Hunter Module (local part that scans and adds to Firestore).
3. Creating the event-driven pipeline (as Firebase Cloud Functions) for processing a paper when it is added to the queue.
4. Creating the self-correction system (as scheduled Cloud Functions).
5. Creating the GraphQL API (as a Firebase HTTP Function).
6. Creating the local idle cycle orchestrator.

Since we are to generate real working code, we'll start by creating the necessary files.

Let's start by creating the Firestore initialization and schema.

Note: We are to use Firebase for state management. We'll assume that the Firebase project is already set up and we have the service account key.

We'll create a file for Firebase initialization and then the main orchestrator.

We are going to create the following files:

1. `firebase_init.py` - Initialize Firebase Admin SDK.
2. `active_hunter.py` - Active Hunter Module that scans for new papers and adds to Firestore.
3. `event_driven_pipeline/` - Directory for Cloud Functions (we'll create separate files for each function).
4. `self_correction_system/` - Directory for self-correction Cloud Functions.
5. `graphql_api/` - Directory for GraphQL server.
6. `idle_orchestrator.py` - Main orchestrator that runs during idle cycles.

However, note that the mission requires a background daemon. We'll create a daemon that runs the Active Hunter and also triggers processing of the queue during idle times.

But note: The event-driven pipeline is designed to be triggered by Firestore events (when a paper is added to the queue). Therefore, the daemon doesn't need to trigger the pipeline directly. Instead, the daemon will run the Active Hunter and also monitor the queue for items that are stuck or need retrying.

Given the complexity and the fact that we are to build a system that works, we'll start by setting up the Firestore and the Active Hunter.

Let's create the files step by step.

First, `firebase_init.py`:

### FILE: firebase_init.py
```python
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_client import BaseClient
import os

# Initialize Firebase Admin SDK
def initialize_firebase():
    # Check if already initialized
    if not firebase_admin._apps:
        # Check for service account key in environment variable or file
        if os.path.exists("serviceAccountKey.json"):
            cred = credentials.Certificate("serviceAccountKey.json")
        elif "FIREBASE_SERVICE_ACCOUNT_KEY_JSON" in os.environ:
            # The environment variable contains the JSON string of the key
            import json
            service_account_info = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT_KEY_JSON"])
            cred = credentials.Certificate(service_account_info)
        else:
            raise FileNotFoundError(
                "Firebase service account key not found. "
                "Either provide a 'serviceAccountKey.json' file or set the "
                "'FIREBASE_SERVICE_ACCOUNT_KEY_JSON' environment variable."
            )
        firebase_admin.initialize_app(cred)
    
    # Return Firestore client
    return firestore.client()

# Firestore client instance
db = initialize_firebase()
```

Next, the Active Hunter Module. We'll create a class that uses the arXiv API and Crossref API to fetch new papers.

### FILE: active_hunter.py
```python
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
```

Now, we need to set up the event-driven pipeline. We'll create Cloud Functions for each step. However, note that we are to build a local daemon that also runs during idle cycles. The Cloud Functions will be triggered by Firestore events, so they will run in the cloud. The local daemon will only run the Active Hunter and maybe monitor the queue.

But note: The mission says "Turns wasted time into foundational research", meaning we want to use idle CPU cycles for processing. Therefore, we might want to run some of the processing locally as well. However, the initial design uses Cloud Functions. We can adjust: the local daemon can process the queue when idle, but we also have Cloud Functions as a backup.

We'll design the system so that the local daemon can process the queue when idle, but we'll also have Cloud Functions that do the same. However, to avoid duplicate processing, we need to manage status in Firestore.

Alternatively, we can design the system to be purely cloud-based for processing, and the local daemon only does the scanning. But the mission says to use idle cycles for processing. Therefore, we'll design the local daemon to process the queue when idle.

Let's adjust: We'll have a local processing pipeline that runs when the system is idle. We'll also have Cloud Functions that can be triggered by Firestore events, but we might disable them if we are running locally to avoid duplicate processing. Alternatively, we can use a hybrid approach where the local daemon processes the queue and updates Firestore, and the Cloud Functions are only for backup or for when the local daemon is not running.

Given the complexity of managing distributed processing, we'll start by building the local processing pipeline. We can later add Cloud Functions for scalability.

We'll create a local processing pipeline with the following steps:

1. PDF Fetcher
2. Text Extractor
3. Semantic Chunker
4. Triple Extractor (using local LLM)
5. Confidence Scorer

We'll create a class for each step and a orchestrator that runs them during idle cycles.

But note: The triple extractor requires a local LLM. We'll use the `transformers` library and a model like Llama 3 8B. However, running this locally requires significant resources. We might need to adjust the idle cycle detection to only run when there is enough GPU memory.

Given the constraints, we'll design the system to be modular and allow for different triple extractors (local or cloud-based).

Let's create the local processing pipeline.

First, the PDF Fetcher:

### FILE: processing_pipeline/pdf_fetcher.py
```python
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
```

Next, the Text Extractor:

### FILE: processing_pipeline/text_extractor.py
```python
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
```

We'll continue with the other components, but note that the triple extractor is complex and requires an LLM. We'll create a placeholder for now.

Given the time, we'll create the main idle cycle orchestrator that runs the Active Hunter and the processing pipeline when the system is idle.

### FILE: idle_orchestrator.py
```python
import psutil
import schedule
import time
import logging
from active_hunter import ActiveHunter
from processing_pipeline.pdf_fetcher import PDFFetcher
from processing_pipeline.text_extractor import TextExtractor

logging.basic