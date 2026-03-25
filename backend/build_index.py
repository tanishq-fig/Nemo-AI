"""
FAISS Vector Index Builder

This script:
1. Loads semantic documents from database
2. Generates embeddings using SentenceTransformers
3. Builds FAISS index for similarity search
4. Saves index to disk for RAG system
"""
import os
import sys
import numpy as np
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer
from typing import List, Tuple

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import ArgoDocument
from config import settings


class VectorIndexBuilder:
    """Build and manage FAISS vector index."""
    
    def __init__(self, model_name: str = None):
        """
        Initialize the index builder.
        
        Args:
            model_name: Name of the SentenceTransformer model
        """
        self.model_name = model_name or settings.EMBEDDING_MODEL
        print(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        print(f"  Embedding dimension: {self.dimension}")
        
    def load_documents(self, db_session) -> Tuple[List[str], List[int]]:
        """
        Load documents from database.
        
        Args:
            db_session: Database session
            
        Returns:
            Tuple of (document texts, vector IDs)
        """
        print("\nLoading documents from database...")
        documents = db_session.query(ArgoDocument).order_by(ArgoDocument.vector_id).all()
        
        texts = [doc.text for doc in documents]
        vector_ids = [doc.vector_id for doc in documents]
        
        print(f"  Loaded {len(texts)} documents")
        return texts, vector_ids
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for texts.
        
        Args:
            texts: List of text strings
            
        Returns:
            Numpy array of embeddings
        """
        print("\nGenerating embeddings...")
        print(f"  Processing {len(texts)} texts...")
        
        # Generate embeddings in batches
        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        print(f"  Generated embeddings shape: {embeddings.shape}")
        return embeddings
    
    def build_faiss_index(self, embeddings: np.ndarray) -> faiss.Index:
        """
        Build FAISS index from embeddings.
        
        Args:
            embeddings: Numpy array of embeddings
            
        Returns:
            FAISS index
        """
        print("\nBuilding FAISS index...")
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Create index (using IndexFlatIP for inner product = cosine similarity)
        index = faiss.IndexFlatIP(self.dimension)
        
        # Add vectors to index
        index.add(embeddings)
        
        print(f"  Index contains {index.ntotal} vectors")
        return index
    
    def save_index(self, index: faiss.Index, index_path: str):
        """
        Save FAISS index to disk.
        
        Args:
            index: FAISS index
            index_path: Path to save index
        """
        print(f"\nSaving index to {index_path}")
        
        # Create directory if needed
        Path(index_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save index
        faiss.write_index(index, index_path)
        print(f"  ✓ Index saved successfully")
    
    def build_and_save(self, index_path: str = None):
        """
        Complete pipeline: load, embed, index, save.
        
        Args:
            index_path: Path to save index (uses config default if None)
        """
        index_path = index_path or settings.FAISS_INDEX_PATH
        
        # Get database session
        db = SessionLocal()
        
        try:
            # Load documents
            texts, vector_ids = self.load_documents(db)
            
            if len(texts) == 0:
                print("\n⚠ No documents found in database!")
                print("   Run 'python ingest.py' first to ingest data")
                return
            
            # Generate embeddings
            embeddings = self.generate_embeddings(texts)
            
            # Build index
            index = self.build_faiss_index(embeddings)
            
            # Save index
            self.save_index(index, index_path)
            
            # Also save a mapping file
            mapping_path = index_path.replace('.bin', '_mapping.npy')
            np.save(mapping_path, np.array(vector_ids))
            print(f"  ✓ Saved vector ID mapping to {mapping_path}")
            
        finally:
            db.close()


def main():
    """Main entry point."""
    print("=" * 60)
    print("FAISS Vector Index Builder")
    print("=" * 60)
    
    # Build index
    builder = VectorIndexBuilder()
    builder.build_and_save()
    
    print("\n" + "=" * 60)
    print("Index Building Complete!")
    print("=" * 60)
    print(f"\nIndex saved to: {settings.FAISS_INDEX_PATH}")
    print(f"Vector index is ready for RAG queries")


if __name__ == "__main__":
    main()
