# upload_data.py

import os
import json
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from tqdm import tqdm
import hashlib

# Import our PDF processor
from pdf_processor import PDFProcessor

class DataUploader:
    def __init__(self, qdrant_url: str = None, qdrant_api_key: str = None):
        """Initialize the data uploader with Qdrant connection."""
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        
        # Initialize Qdrant client
        try:
            self.qdrant_client = QdrantClient(
                url=qdrant_url or os.getenv("QDRANT_URL"),
                api_key=qdrant_api_key or os.getenv("QDRANT_API_KEY")
            )
            print("✅ Qdrant connection established")
        except Exception as e:
            print(f"❌ Failed to connect to Qdrant: {e}")
            self.qdrant_client = None
    
    def create_collection(self, collection_name: str = "ksa_legal_docs"):
        """Create or recreate the collection in Qdrant."""
        if not self.qdrant_client:
            print("❌ Qdrant client not available")
            return False
        
        try:
            # Delete existing collection if it exists
            try:
                self.qdrant_client.delete_collection(collection_name)
                print(f"🗑️ Deleted existing collection: {collection_name}")
            except:
                pass
            
            # Create new collection
            self.qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.embedder.get_sentence_embedding_dimension(),
                    distance=Distance.COSINE
                )
            )
            print(f"✅ Created collection: {collection_name}")
            return True
        except Exception as e:
            print(f"❌ Failed to create collection: {e}")
            return False
    
    def upload_documents(self, documents: List[Dict[str, Any]], collection_name: str = "ksa_legal_docs"):
        """Upload documents to Qdrant with embeddings."""
        if not self.qdrant_client:
            print("❌ Qdrant client not available")
            return False
        
        if not documents:
            print("❌ No documents to upload")
            return False
        
        print(f"📤 Uploading {len(documents)} documents to Qdrant...")
        
        # Process documents in batches
        batch_size = 100
        points = []
        
        for i, doc in enumerate(tqdm(documents, desc="Processing documents")):
            try:
                # Generate embedding
                text = doc.get("text", "")
                if not text.strip():
                    continue
                
                embedding = self.embedder.encode(text, normalize_embeddings=True).tolist()
                
                # Create point
                point = PointStruct(
                    id=doc.get("id", str(i)),
                    vector=embedding,
                    payload={
                        "text": text,
                        "title": doc.get("title", ""),
                        "source": doc.get("source", "unknown"),
                        "law_type": doc.get("law_type", "general"),
                        "filename": doc.get("filename", ""),
                        "chunk_index": doc.get("chunk_index", 0),
                        "metadata": doc.get("metadata", {})
                    }
                )
                points.append(point)
                
                # Upload batch when full
                if len(points) >= batch_size:
                    self.qdrant_client.upsert(
                        collection_name=collection_name,
                        points=points
                    )
                    points = []
                    
            except Exception as e:
                print(f"❌ Error processing document {i}: {e}")
                continue
        
        # Upload remaining points
        if points:
            try:
                self.qdrant_client.upsert(
                    collection_name=collection_name,
                    points=points
                )
            except Exception as e:
                print(f"❌ Error uploading final batch: {e}")
        
        print(f"✅ Upload completed!")
        return True
    
    def load_cases_data(self, cases_file: str = "all_unique_fields.json"):
        """Load existing cases data."""
        try:
            with open(cases_file, 'r', encoding='utf-8') as f:
                cases_data = json.load(f)
            
            # Convert cases to document format
            documents = []
            for i, case in enumerate(cases_data):
                if isinstance(case, dict) and "summary" in case:
                    doc_id = hashlib.md5(f"case_{i}".encode()).hexdigest()
                    document = {
                        "id": doc_id,
                        "title": case.get("case_id", f"Case {i}"),
                        "text": case.get("summary", ""),
                        "source": "case",
                        "law_type": "case_law",
                        "filename": f"case_{i}",
                        "chunk_index": 0,
                        "metadata": case
                    }
                    documents.append(document)
            
            print(f"📄 Loaded {len(documents)} cases from {cases_file}")
            return documents
        except Exception as e:
            print(f"❌ Error loading cases: {e}")
            return []
    
    def process_and_upload_pdfs(self, pdf_dir: str = "../../LAWGPT_KSA_data"):
        """Process PDFs and upload them to Qdrant."""
        print("📚 Processing PDF documents...")
        
        processor = PDFProcessor(pdf_dir)
        pdf_documents = processor.process_all_pdfs()
        
        if pdf_documents:
            print(f"📄 Processed {len(pdf_documents)} PDF chunks")
            return pdf_documents
        else:
            print("❌ No PDF documents processed")
            return []
    
    def upload_all_data(self, collection_name: str = "ksa_legal_docs"):
        """Upload both cases and PDFs to Qdrant."""
        if not self.create_collection(collection_name):
            return False
        
        all_documents = []
        
        # Load and process cases
        print("🔍 Loading existing cases...")
        cases = self.load_cases_data()
        all_documents.extend(cases)
        
        # Process and add PDFs
        print("📚 Processing PDF documents...")
        pdfs = self.process_and_upload_pdfs()
        all_documents.extend(pdfs)
        
        if not all_documents:
            print("❌ No documents to upload")
            return False
        
        print(f"📊 Total documents to upload: {len(all_documents)}")
        print(f"  - Cases: {len(cases)}")
        print(f"  - PDF chunks: {len(pdfs)}")
        
        # Upload all documents
        return self.upload_documents(all_documents, collection_name)
    
    def get_collection_info(self, collection_name: str = "ksa_legal_docs"):
        """Get information about the collection."""
        if not self.qdrant_client:
            print("❌ Qdrant client not available")
            return
        
        try:
            info = self.qdrant_client.get_collection(collection_name)
            print(f"📊 Collection info for '{collection_name}':")
            print(f"  - Points count: {info.points_count}")
            print(f"  - Vectors config: {info.config.params.vectors}")
        except Exception as e:
            print(f"❌ Error getting collection info: {e}")

def main():
    """Main function to upload all data."""
    print("🚀 Starting KSA Legal Data Upload...")
    
    uploader = DataUploader()
    
    if uploader.qdrant_client is None:
        print("❌ Cannot proceed without Qdrant connection")
        return
    
    # Upload all data
    success = uploader.upload_all_data()
    
    if success:
        print("✅ Data upload completed successfully!")
        uploader.get_collection_info()
    else:
        print("❌ Data upload failed")

if __name__ == "__main__":
    main()
