# pdf_processor.py

import os
import re
from typing import List, Dict, Any
from pathlib import Path
import PyPDF2
from pypdf import PdfReader
import hashlib
from tqdm import tqdm

class PDFProcessor:
    def __init__(self, pdf_dir: str = r"C:\Users\pc\Desktop\Internship 2025\LAWGPT_KSA\LAWGPT_KSA_data"):
        self.pdf_dir = Path(pdf_dir)
        self.processed_docs = []
    
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract text from a PDF file using multiple methods for better results."""
        try:
            # Try with PyPDF2 first
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            
            # If text is too short, try with pypdf
            if len(text.strip()) < 100:
                reader = PdfReader(pdf_path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            
            return text.strip()
        except Exception as e:
            print(f"Error extracting text from {pdf_path}: {e}")
            return ""
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove page numbers and headers
        text = re.sub(r'Page \d+ of \d+', '', text)
        text = re.sub(r'\d+\s*of\s*\d+', '', text)
        # Remove special characters but keep Arabic text
        text = re.sub(r'[^\w\s\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF.,!?;:()\[\]{}"\'-]', '', text)
        return text.strip()
    
    def split_text_into_chunks(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks for better embedding."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundaries
            if end < len(text):
                # Look for sentence endings
                for i in range(end, max(start + chunk_size - 200, start), -1):
                    if text[i] in '.!?':
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks
    
    def process_pdf(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Process a single PDF file and return structured data."""
        print(f"Processing: {pdf_path.name}")
        
        # Extract text
        raw_text = self.extract_text_from_pdf(pdf_path)
        if not raw_text:
            return []
        
        # Clean text
        cleaned_text = self.clean_text(raw_text)
        
        # Split into chunks
        chunks = self.split_text_into_chunks(cleaned_text)
        
        # Create structured data
        documents = []
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < 50:  # Skip very short chunks
                continue
                
            doc_id = hashlib.md5(f"{pdf_path.name}_{i}".encode()).hexdigest()
            
            document = {
                "id": doc_id,
                "title": pdf_path.stem,
                "filename": pdf_path.name,
                "chunk_index": i,
                "text": chunk,
                "source": "pdf",
                "law_type": self.categorize_law(pdf_path.name),
                "metadata": {
                    "file_path": str(pdf_path),
                    "total_chunks": len(chunks),
                    "chunk_size": len(chunk)
                }
            }
            documents.append(document)
        
        print(f"  Created {len(documents)} chunks from {pdf_path.name}")
        return documents
    
    def categorize_law(self, filename: str) -> str:
        """Categorize the law based on filename."""
        filename_lower = filename.lower()
        
        if "civil" in filename_lower:
            return "civil_law"
        elif "criminal" in filename_lower:
            return "criminal_law"
        elif "labor" in filename_lower:
            return "labor_law"
        elif "company" in filename_lower:
            return "company_law"
        elif "traffic" in filename_lower:
            return "traffic_law"
        elif "sharia" in filename_lower:
            return "sharia_law"
        elif "board" in filename_lower and "grievance" in filename_lower:
            return "administrative_law"
        elif "basic" in filename_lower and "governance" in filename_lower:
            return "constitutional_law"
        else:
            return "general_law"
    
    def process_all_pdfs(self) -> List[Dict[str, Any]]:
        """Process all PDF files in the directory."""
        pdf_files = list(self.pdf_dir.glob("*.pdf"))
        
        if not pdf_files:
            print(f"No PDF files found in {self.pdf_dir}")
            return []
        
        print(f"Found {len(pdf_files)} PDF files to process")
        
        all_documents = []
        
        for pdf_file in tqdm(pdf_files, desc="Processing PDFs"):
            try:
                documents = self.process_pdf(pdf_file)
                all_documents.extend(documents)
            except Exception as e:
                print(f"Error processing {pdf_file}: {e}")
                continue
        
        print(f"Total documents created: {len(all_documents)}")
        return all_documents
    
    def save_processed_data(self, documents: List[Dict[str, Any]], output_file: str = "processed_pdfs.json"):
        """Save processed documents to JSON file."""
        import json
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(documents, f, ensure_ascii=False, indent=2)
        
        print(f"Saved {len(documents)} documents to {output_file}")

def main():
    """Main function to process PDFs."""
    processor = PDFProcessor()
    documents = processor.process_all_pdfs()
    
    if documents:
        processor.save_processed_data(documents)
        print("PDF processing completed successfully!")
    else:
        print("No documents were processed.")

if __name__ == "__main__":
    main() 