"""
Vector Database Integration for Agent Memory
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum

from .logger import get_logger

logger = get_logger(__name__)


class VectorDistance(Enum):
    """Distance metrics"""
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT = "dot"


@dataclass
class Vector:
    """Vector representation"""
    id: str
    values: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """Search result"""
    vector: Vector
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class VectorStore(ABC):
    """
    Abstract vector store interface
    
    Provides:
    - Vector storage
    - Similarity search
    - Metadata filtering
    - Batch operations
    """
    
    @abstractmethod
    async def add_vector(self, vector: Vector) -> bool:
        """
        Add a vector to the store
        
        Args:
            vector: Vector to add
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def add_vectors(self, vectors: List[Vector]) -> bool:
        """
        Add multiple vectors
        
        Args:
            vectors: List of vectors
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        distance: VectorDistance = VectorDistance.COSINE
    ) -> List[SearchResult]:
        """
        Search for similar vectors
        
        Args:
            query_vector: Query vector
            top_k: Number of results
            distance: Distance metric
            
        Returns:
            List of search results
        """
        pass
    
    @abstractmethod
    async def delete_vector(self, vector_id: str) -> bool:
        """
        Delete a vector
        
        Args:
            vector_id: Vector ID
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def get_vector(self, vector_id: str) -> Optional[Vector]:
        """
        Get a vector by ID
        
        Args:
            vector_id: Vector ID
            
        Returns:
            Vector or None
        """
        pass
    
    @abstractmethod
    async def list_vectors(self, limit: int = 100) -> List[Vector]:
        """
        List all vectors
        
        Args:
            limit: Maximum number
            
        Returns:
            List of vectors
        """
        pass


class InMemoryVectorStore(VectorStore):
    """
    In-memory vector store for testing and development
    
    Provides:
    - Simple vector storage
    - Cosine similarity search
    - Metadata filtering
    """
    
    def __init__(self):
        """Initialize in-memory store"""
        self.vectors: Dict[str, Vector] = {}
        self._lock = asyncio.Lock()
    
    async def add_vector(self, vector: Vector) -> bool:
        """Add a vector"""
        async with self._lock:
            self.vectors[vector.id] = vector
            return True
    
    async def add_vectors(self, vectors: List[Vector]) -> bool:
        """Add multiple vectors"""
        async with self._lock:
            for vector in vectors:
                self.vectors[vector.id] = vector
            return True
    
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        distance: VectorDistance = VectorDistance.COSINE
    ) -> List[SearchResult]:
        """Search for similar vectors"""
        results = []
        
        for vector in self.vectors.values():
            score = self._compute_distance(
                query_vector,
                vector.values,
                distance
            )
            results.append(SearchResult(
                vector=vector,
                score=score,
                metadata=vector.metadata
            ))
        
        # Sort by score (lower is better for distance)
        results.sort(key=lambda x: x.score)
        
        return results[:top_k]
    
    async def delete_vector(self, vector_id: str) -> bool:
        """Delete a vector"""
        async with self._lock:
            if vector_id in self.vectors:
                del self.vectors[vector_id]
                return True
            return False
    
    async def get_vector(self, vector_id: str) -> Optional[Vector]:
        """Get a vector"""
        return self.vectors.get(vector_id)
    
    async def list_vectors(self, limit: int = 100) -> List[Vector]:
        """List vectors"""
        return list(self.vectors.values())[:limit]
    
    def _compute_distance(
        self,
        vec1: List[float],
        vec2: List[float],
        distance: VectorDistance
    ) -> float:
        """Compute distance between vectors"""
        if len(vec1) != len(vec2):
            return float('inf')
        
        if distance == VectorDistance.COSINE:
            return self._cosine_distance(vec1, vec2)
        elif distance == VectorDistance.EUCLIDEAN:
            return self._euclidean_distance(vec1, vec2)
        elif distance == VectorDistance.DOT:
            return -self._dot_product(vec1, vec2)
        else:
            return float('inf')
    
    def _cosine_distance(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine distance"""
        dot = self._dot_product(vec1, vec2)
        norm1 = sum(x * x for x in vec1) ** 0.5
        norm2 = sum(x * x for x in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 1.0
        
        return 1.0 - (dot / (norm1 * norm2))
    
    def _euclidean_distance(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute Euclidean distance"""
        return sum((a - b) ** 2 for a, b in zip(vec1, vec2)) ** 0.5
    
    def _dot_product(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute dot product"""
        return sum(a * b for a, b in zip(vec1, vec2))


class MemoryStore:
    """
    Memory store with vector search
    
    Provides:
    - Long-term memory storage
    - Semantic search
    - Context retrieval
    - Memory management
    """
    
    def __init__(self, vector_store: VectorStore):
        """
        Initialize memory store
        
        Args:
            vector_store: Vector store backend
        """
        self.vector_store = vector_store
        self._lock = asyncio.Lock()
    
    async def store_memory(
        self,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Store a memory
        
        Args:
            content: Content to store
            embedding: Vector embedding
            metadata: Optional metadata
            
        Returns:
            Memory ID
        """
        import uuid
        
        memory_id = str(uuid.uuid4())
        
        vector = Vector(
            id=memory_id,
            values=embedding,
            metadata={
                "content": content,
                **(metadata or {})
            }
        )
        
        await self.vector_store.add_vector(vector)
        
        logger.info(f"Stored memory: {memory_id}")
        return memory_id
    
    async def retrieve_memories(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar memories
        
        Args:
            query_embedding: Query vector
            top_k: Number of results
            filters: Metadata filters
            
        Returns:
            List of memories
        """
        results = await self.vector_store.search(
            query_embedding,
            top_k=top_k
        )
        
        # Apply filters
        if filters:
            results = [
                r for r in results
                if all(
                    r.metadata.get(k) == v
                    for k, v in filters.items()
                )
            ]
        
        return [
            {
                "id": r.vector.id,
                "content": r.metadata.get("content"),
                "score": r.score,
                "metadata": r.metadata
            }
            for r in results
        ]
    
    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a memory by ID
        
        Args:
            memory_id: Memory ID
            
        Returns:
            Memory or None
        """
        vector = await self.vector_store.get_vector(memory_id)
        
        if not vector:
            return None
        
        return {
            "id": vector.id,
            "content": vector.metadata.get("content"),
            "metadata": vector.metadata
        }
    
    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory
        
        Args:
            memory_id: Memory ID
            
        Returns:
            True if successful
        """
        return await self.vector_store.delete_vector(memory_id)
    
    async def list_memories(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List all memories
        
        Args:
            limit: Maximum number
            
        Returns:
            List of memories
        """
        vectors = await self.vector_store.list_vectors(limit)
        
        return [
            {
                "id": v.id,
                "content": v.metadata.get("content"),
                "metadata": v.metadata
            }
            for v in vectors
        ]


class EmbeddingModel:
    """
    Embedding model for text
    
    Provides:
    - Text to embedding conversion
    - Batch embedding
    - Model management
    """
    
    def __init__(self, model_name: str = "default"):
        """
        Initialize embedding model
        
        Args:
            model_name: Model name
        """
        self.model_name = model_name
        logger.info(f"Initialized embedding model: {model_name}")
    
    async def embed(self, text: str) -> List[float]:
        """
        Embed text
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        # Simple hash-based embedding for demo
        # In production, use actual embedding model
        import hashlib
        
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to float vector
        embedding = [float(b) / 255.0 for b in hash_bytes[:128]]
        
        # Pad to 128 dimensions
        embedding.extend([0.0] * (128 - len(embedding)))
        
        return embedding
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple texts
        
        Args:
            texts: List of texts
            
        Returns:
            List of embeddings
        """
        embeddings = []
        
        for text in texts:
            embedding = await self.embed(text)
            embeddings.append(embedding)
        
        return embeddings


def get_memory_store() -> MemoryStore:
    """Get global memory store instance"""
    if not hasattr(get_memory_store, "_instance"):
        vector_store = InMemoryVectorStore()
        get_memory_store._instance = MemoryStore(vector_store)
    return get_memory_store._instance


def get_embedding_model() -> EmbeddingModel:
    """Get global embedding model instance"""
    if not hasattr(get_embedding_model, "_instance"):
        get_embedding_model._instance = EmbeddingModel()
    return get_embedding_model._instance
