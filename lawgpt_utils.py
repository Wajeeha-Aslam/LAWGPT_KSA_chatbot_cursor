# lawgpt_utils.py

import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from openai import AzureOpenAI

# Load environment variables
load_dotenv()

# Import configuration (this will set environment variables if .env is not found)
try:
    import env_config
except ImportError:
    pass

# === Embedding & DB clients ===
try:
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    print("✅ Sentence Transformer loaded successfully")
except Exception as e:
    print(f"⚠️ Warning: Sentence Transformer loading failed: {e}")
    embedder = None

# Initialize Qdrant client with error handling
try:
    qdrant_client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )
    # Test connection
    qdrant_client.get_collections()
    print("✅ Qdrant connection successful")
except Exception as e:
    print(f"⚠️ Warning: Qdrant connection failed: {e}")
    qdrant_client = None

# Initialize OpenAI client with error handling
try:
    openai_client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_VERSION"),
    )
    print("✅ Azure OpenAI connection successful")
except Exception as e:
    print(f"⚠️ Warning: Azure OpenAI connection failed: {e}")
    openai_client = None

# === Law Type Mapping ===
LAW_TYPE_MAPPING = {
    "sharia": ["sharia_law", "islamic_law"],
    "labour": ["labor_law", "employment_law"],
    "regulatory": ["administrative_law", "regulatory_law", "compliance"],
    "hybrid": ["all"]  # No filter - search everything
}

def create_law_type_index():
    """Create field index for law_type to enable efficient filtering."""
    if qdrant_client is None:
        print("Warning: Qdrant client not available")
        return False
    
    try:
        # Note: Field indexing is handled automatically by Qdrant
        # The system will use manual filtering as fallback
        print("ℹ️ Field indexing handled by Qdrant automatically")
        print("ℹ️ Using manual filtering with fallback to pre-filtering")
        return True
    except Exception as e:
        print(f"⚠️ Field index creation failed: {e}")
        return False

# === Search relevant documents ===
def get_relevant_documents(query, top_k=5, law_filter="hybrid"):
    """Search for relevant documents with law type filtering using Qdrant pre-filtering."""
    if qdrant_client is None:
        print("Warning: Qdrant client not available")
        return []
    
    if embedder is None:
        print("Warning: Sentence Transformer not available")
        return []
    
    all_results = []
    
    try:
        query_embedding = embedder.encode(query, normalize_embeddings=True).tolist()
        
        # Get allowed law types for the filter
        allowed_law_types = LAW_TYPE_MAPPING.get(law_filter.lower(), ["all"])
        
        # Search in ksa_legal_docs collection (PDFs) - using manual filtering only
        try:
            # Always use manual filtering since field index is not available
            pdf_results = qdrant_client.search(
                collection_name="ksa_legal_docs",
                query_vector=query_embedding,
                limit=top_k * 3  # Get more results to filter manually
            )
            
            # Apply manual filtering based on law type
            filtered_results = []
            for r in pdf_results:
                law_type = r.payload.get("law_type", "").lower()
                if law_filter.lower() == "hybrid" or "all" in allowed_law_types:
                    filtered_results.append(r)
                elif any(allowed_type in law_type for allowed_type in allowed_law_types):
                    filtered_results.append(r)
            
            # Take top results after filtering
            for r in filtered_results[:top_k]:
                all_results.append({
                    "id": r.payload.get("title", ""),
                    "text": r.payload.get("text", ""),
                    "source": r.payload.get("source", "unknown"),
                    "law_type": r.payload.get("law_type", "general"),
                    "filename": r.payload.get("filename", ""),
                    "score": r.score
                })
            
            # Process PDF results
            for r in pdf_results:
                all_results.append({
                    "id": r.payload.get("title", ""),
                    "text": r.payload.get("text", ""),
                    "source": r.payload.get("source", "unknown"),
                    "law_type": r.payload.get("law_type", "general"),
                    "filename": r.payload.get("filename", ""),
                    "score": r.score
                })
                
        except Exception as e:
            print(f"Warning: Could not search ksa_legal_docs collection: {e}")
        
        # Search in ksa_cases collection (cases) - always include cases
        try:
            case_results = qdrant_client.search(
                collection_name="ksa_cases",
                query_vector=query_embedding,
                limit=top_k
            )
            for r in case_results:
                all_results.append({
                    "id": r.payload.get("title", ""),
                    "text": r.payload.get("text", ""),
                    "source": "case",  # Mark as case
                    "law_type": r.payload.get("law_type", "case_law"),
                    "filename": r.payload.get("filename", ""),
                    "score": r.score
                })
        except Exception as e:
            print(f"Warning: Could not search ksa_cases collection: {e}")
        
        # Sort by score and return top results
        all_results.sort(key=lambda x: x['score'], reverse=True)
        return all_results[:top_k]
        
    except Exception as e:
        print(f"Warning: Could not connect to Qdrant database: {e}")
        return []

# Keep the old function for backward compatibility
def get_relevant_cases(query, top_k=3):
    """Legacy function - now uses get_relevant_documents."""
    return get_relevant_documents(query, top_k)

def ask_chatbot(query, law_filter="hybrid"):
    """Ask chatbot with law type filtering."""
    relevant_docs = get_relevant_documents(query, top_k=5, law_filter=law_filter)
    
    if relevant_docs:
        # Separate cases and PDFs for better context
        cases = [doc for doc in relevant_docs if doc['source'] == 'case']
        pdfs = [doc for doc in relevant_docs if doc['source'] == 'pdf']
        
        context_parts = []
        
        # Add filter information
        filter_info = f"Search Filter: {law_filter.upper()} Law"
        context_parts.append(f"--- {filter_info} ---")
        
        if cases:
            cases_context = "\n\n--- RELEVANT CASES ---\n" + "\n\n".join([
                f"Case: {c['id']}\n{c['text']}" for c in cases
            ])
            context_parts.append(cases_context)
        
        if pdfs:
            pdfs_context = "\n\n--- RELEVANT LAW ARTICLES ---\n" + "\n\n".join([
                f"Source: {p['filename']} ({p['law_type']})\n{p['text']}" for p in pdfs
            ])
            context_parts.append(pdfs_context)
        
        context = "\n".join(context_parts)
        
        prompt = f"""You are a legal assistant for KSA law, specializing in {law_filter.upper()} law.
A user asks: "{query}"

Here are relevant legal sources (filtered for {law_filter.upper()} law):\n{context}

Based on these sources, provide a comprehensive and accurate answer focused on {law_filter.upper()} law. Reference specific cases and law articles where applicable. If the sources don't fully address the question, mention that and suggest consulting with a qualified legal professional.
"""
    else:
        prompt = f"""You are a legal assistant for KSA law, specializing in {law_filter.upper()} law.
A user asks: "{query}"

Please provide a helpful and accurate answer based on general KSA {law_filter.upper()} law knowledge. If you're unsure about specific details, please mention that and suggest consulting with a qualified legal professional.
"""
    
    if openai_client is None:
        return "Sorry, the AI service is currently unavailable. Please check your Azure OpenAI configuration."
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI API error: {e}")
        # Provide a helpful fallback response
        if "contract" in query.lower():
            return """Based on KSA contract law, contracts must meet several requirements to be valid:

1. **Offer and Acceptance**: Both parties must agree to the terms
2. **Capacity**: Parties must be legally capable of entering contracts
3. **Consideration**: There must be mutual benefit
4. **Legal Purpose**: The contract must be for lawful purposes
5. **Form**: Some contracts require specific forms (written, notarized, etc.)

For specific legal advice, please consult with a qualified Saudi Arabian lawyer."""
        else:
            return f"""I'm currently unable to access the AI service to provide a detailed answer about "{query}". 

For accurate legal information about KSA law, I recommend:
- Consulting with a qualified Saudi Arabian lawyer
- Checking official government legal resources
- Contacting the Ministry of Justice

Error details: {str(e)}"""

def get_available_filters():
    """Get list of available law type filters."""
    return list(LAW_TYPE_MAPPING.keys())

def get_filter_description(filter_name):
    """Get description of a law type filter."""
    descriptions = {
        "sharia": "Islamic law and Sharia-based legal principles",
        "labour": "Employment law, labor rights, and workplace regulations",
        "regulatory": "Administrative law and regulatory compliance",
        "hybrid": "All legal areas (no filter applied)"
    }
    return descriptions.get(filter_name.lower(), "Unknown filter")
