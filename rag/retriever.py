"""
RAG Retriever for GeneTrustAI-Thal.
Handles semantic search over the ChromaDB vector store.
"""

from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

BASE_DIR = Path(__file__).resolve().parent.parent
RAG_DIR = BASE_DIR / "rag"
DB_DIR = RAG_DIR / "chroma_db"

class ClinicalRetriever:
    def __init__(self):
        try:
            self.client = chromadb.PersistentClient(path=str(DB_DIR))
            self.ef = embedding_functions.DefaultEmbeddingFunction()
            self.collection = self.client.get_collection(
                name="genetrust_knowledge",
                embedding_function=self.ef
            )
            self.ready = True
        except Exception as e:
            print(f"⚠ Warning: Could not initialize ChromaDB retriever: {e}")
            self.ready = False

    def retrieve_context(self, query: str, n_results: int = 5) -> str:
        """
        Search the vector database for clinical knowledge related to the query.
        Returns a formatted string of the retrieved documents.
        """
        if not self.ready:
            return "Knowledge base not available."

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            docs = results['documents'][0]
            metadatas = results['metadatas'][0]
            
            context_parts = []
            for doc, meta in zip(docs, metadatas):
                source = meta.get("source", "unknown")
                if source == "clinical_kb":
                    topic = meta.get("topic", "")
                    context_parts.append(f"[Clinical Knowledge - {topic}]\n{doc}")
                else:
                    context_parts.append(f"[Variant Database]\n{doc}")
                    
            return "\n\n---\n\n".join(context_parts)
        except Exception as e:
            print(f"Retrieval error: {e}")
            return "Error retrieving context."

# Lazy Initialization Singleton
_retriever_instance = None

def get_retriever():
    global _retriever_instance
    if _retriever_instance is None:
        print("Initializing ClinicalRetriever lazily...")
        _retriever_instance = ClinicalRetriever()
    return _retriever_instance
