# -*- coding: utf-8 -*-
"""
RAG Engine - Retrieval Augmented Generation for ASCET Code
Provides embeddings, vector similarity search, and context retrieval
"""

import os
import sys
import json
import hashlib
import pickle
import time
import random
from typing import List, Dict, Optional, Tuple
from pathlib import Path

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False


class RateLimiter:
    """Token bucket algorithm for request rate limiting"""
    
    def __init__(self, rate=60, per=60, burst=10):
        self.rate = rate      # Requests per 'per' seconds
        self.per = per        # Time period in seconds
        self.burst = burst    # Max burst requests
        self.tokens = burst
        self.last_time = time.time()
    
    def acquire(self, timeout=60):
        """Acquire a token, wait if necessary"""
        start = time.time()
        while time.time() - start < timeout:
            current = time.time()
            elapsed = current - self.last_time
            self.last_time = current
            
            # Refill tokens
            self.tokens += elapsed * (self.rate / self.per)
            if self.tokens > self.burst:
                self.tokens = self.burst
            
            # Check if we have tokens
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            
            # Wait and retry
            wait_time = (1 - self.tokens) * (self.per / self.rate)
            time.sleep(min(wait_time, 0.1))
        
        return False


class EmbeddingGenerator:
    """Generates text embeddings (stub for CLI - would use real API in production)"""
    
    def __init__(self, api_key: str = "", 
                 api_url: str = "", 
                 model: str = "text-embedding-3-small",
                 cache_dir: str = "embedding_cache"):
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.cache_dir = cache_dir
        self.rate_limiter = RateLimiter(rate=15, per=60, burst=3)
        
        # Create cache dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_path(self, text: str) -> str:
        """Get cache file path for text"""
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        return os.path.join(self.cache_dir, f"{text_hash}.pkl")
    
    def _check_cache(self, text: str) -> Optional[List[float]]:
        """Check if embedding is cached"""
        cache_path = self._get_cache_path(text)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"[RAG] Cache read error: {e}", file=sys.stderr)
        return None
    
    def _save_to_cache(self, text: str, embedding: List[float]):
        """Save embedding to cache"""
        cache_path = self._get_cache_path(text)
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(embedding, f)
        except Exception as e:
            print(f"[RAG] Cache write error: {e}", file=sys.stderr)
    
    def create_embedding(self, text: str) -> Optional[List[float]]:
        """
        Create embedding for text.
        
        This is a stub implementation. In production, would call actual API.
        For CLI usage, returns a deterministic hash-based embedding.
        """
        # Check cache first
        cached = self._check_cache(text)
        if cached:
            print(f"[RAG] Cache hit for text (len={len(text)})", file=sys.stderr)
            return cached
        
        # Stub: Create deterministic embedding from text hash
        # In production, would call embedding API
        hash_val = hashlib.sha256(text.encode('utf-8')).digest()
        
        # Create 384-dimensional embedding (text-embedding-3-small dimensions)
        embedding = []
        for i in range(384):
            byte_idx = i % len(hash_val)
            embedding.append((hash_val[byte_idx] / 255.0) - 0.5)
        
        # Normalize
        if NUMPY_AVAILABLE:
            embedding = np.array(embedding)
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = (embedding / norm).tolist()
        
        # Cache it
        self._save_to_cache(text, embedding)
        print(f"[RAG] Embedding created for text (len={len(text)})", file=sys.stderr)
        
        return embedding


class RAGEngine:
    """
    RAG Engine for ASCET Code Analysis
    Retrieves similar defects/patterns from knowledge base
    """
    
    def __init__(self, index_path: str = "knowledge_base.index", 
                 cache_dir: str = "embedding_cache"):
        self.index_path = index_path
        self.cache_dir = cache_dir
        self.embedding_gen = EmbeddingGenerator(cache_dir=cache_dir)
        self.faiss_index = None
        self.doc_store = {}  # Maps index IDs to original documents
        
        # Try to load existing index
        self._load_index()
    
    def _load_index(self):
        """Load FAISS index if it exists"""
        if os.path.exists(self.index_path):
            try:
                if FAISS_AVAILABLE:
                    self.faiss_index = faiss.read_index(self.index_path)
                    print(f"[RAG] Loaded FAISS index: {self.index_path}", file=sys.stderr)
            except Exception as e:
                print(f"[RAG] Failed to load index: {e}", file=sys.stderr)
                self.faiss_index = None
    
    def _create_index(self, dimension: int = 384):
        """Create new FAISS index"""
        if FAISS_AVAILABLE:
            self.faiss_index = faiss.IndexFlatL2(dimension)
            print(f"[RAG] Created new FAISS index (dimension={dimension})", file=sys.stderr)
    
    def add_to_knowledge_base(self, doc_id: str, text: str, metadata: Dict = None):
        """Add document to knowledge base"""
        try:
            embedding = self.embedding_gen.create_embedding(text)
            if not embedding:
                print(f"[RAG] Failed to create embedding for {doc_id}", file=sys.stderr)
                return False
            
            # Store document
            self.doc_store[doc_id] = {
                "text": text,
                "metadata": metadata or {},
                "embedding": embedding
            }
            
            # Initialize index if needed
            if self.faiss_index is None:
                self._create_index(len(embedding))
            
            # Add to FAISS
            if FAISS_AVAILABLE and self.faiss_index:
                import numpy as np
                vectors = np.array([embedding], dtype=np.float32)
                doc_id_num = len(self.doc_store) - 1
                self.faiss_index.add(vectors)
                print(f"[RAG] Added doc {doc_id} to index", file=sys.stderr)
            
            return True
            
        except Exception as e:
            print(f"[RAG] Error adding to KB: {e}", file=sys.stderr)
            return False
    
    def retrieve_similar_defects(self, code_context: str, top_k: int = 3) -> List[Dict]:
        """
        Retrieve similar code patterns or defects from knowledge base.
        Returns list of similar documents with relevance scores.
        """
        try:
            if not self.faiss_index or not self.doc_store:
                print(f"[RAG] No knowledge base available (index={self.faiss_index}, docs={len(self.doc_store)})", file=sys.stderr)
                return []
            
            # Create query embedding
            query_embedding = self.embedding_gen.create_embedding(code_context)
            if not query_embedding:
                print(f"[RAG] Failed to create query embedding", file=sys.stderr)
                return []
            
            # Search in FAISS
            if NUMPY_AVAILABLE:
                import numpy as np
                query_vector = np.array([query_embedding], dtype=np.float32)
                distances, indices = self.faiss_index.search(query_vector, min(top_k, len(self.doc_store)))
                
                results = []
                for idx, distance in zip(indices[0], distances[0]):
                    if 0 <= idx < len(self.doc_store):
                        doc_id = list(self.doc_store.keys())[idx]
                        doc = self.doc_store[doc_id]
                        results.append({
                            "doc_id": doc_id,
                            "similarity_score": float(1 / (1 + distance)),  # Convert distance to similarity
                            "text": doc["text"][:500],  # Truncate for readability
                            "metadata": doc["metadata"]
                        })
                
                print(f"[RAG] Retrieved {len(results)} similar documents", file=sys.stderr)
                return results
            else:
                print(f"[RAG] NumPy not available for FAISS search", file=sys.stderr)
                return []
        
        except Exception as e:
            print(f"[RAG] Retrieval error: {e}", file=sys.stderr)
            return []
    
    def save_index(self):
        """Save FAISS index to disk"""
        if FAISS_AVAILABLE and self.faiss_index:
            try:
                faiss.write_index(self.faiss_index, self.index_path)
                print(f"[RAG] Index saved to {self.index_path}", file=sys.stderr)
                return True
            except Exception as e:
                print(f"[RAG] Failed to save index: {e}", file=sys.stderr)
        return False


# Module-level convenience functions
_rag_instance = None

def get_rag_engine() -> RAGEngine:
    """Get global RAG engine instance"""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGEngine()
    return _rag_instance

def retrieve_similar_code(code_context: str, top_k: int = 3) -> List[Dict]:
    """Convenience function to retrieve similar code patterns"""
    engine = get_rag_engine()
    return engine.retrieve_similar_defects(code_context, top_k=top_k)
