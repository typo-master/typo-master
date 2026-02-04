"""
Agent Knowledge Base Management
"""

import json
import time
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .logger import get_logger

logger = get_logger(__name__)


class KnowledgeType(Enum):
    """Types of knowledge"""
    FACT = "fact"
    RULE = "rule"
    PROCEDURE = "procedure"
    EXAMPLE = "example"
    PATTERN = "pattern"


@dataclass
class Knowledge:
    """Knowledge item"""
    id: str
    type: KnowledgeType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class KnowledgeBase:
    """
    Knowledge base for agents
    
    Provides:
    - Knowledge storage
    - Knowledge retrieval
    - Knowledge indexing
    - Knowledge validation
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize knowledge base
        
        Args:
            storage_path: Path to storage file
        """
        self.storage_path = storage_path
        self.knowledge: Dict[str, Knowledge] = {}
        self.index: Dict[str, Set[str]] = {}  # tag -> knowledge ids
        self._lock = None
        
        if storage_path:
            self._load_from_storage()
    
    def add_knowledge(
        self,
        content: str,
        knowledge_type: KnowledgeType,
        tags: Set[str] = None,
        metadata: Dict[str, Any] = None,
        confidence: float = 1.0
    ) -> str:
        """
        Add knowledge to the base
        
        Args:
            content: Knowledge content
            knowledge_type: Type of knowledge
            tags: Tags for indexing
            metadata: Additional metadata
            confidence: Confidence score
            
        Returns:
            Knowledge ID
        """
        import uuid
        
        knowledge_id = str(uuid.uuid4())
        
        knowledge = Knowledge(
            id=knowledge_id,
            type=knowledge_type,
            content=content,
            metadata=metadata or {},
            tags=tags or set(),
            confidence=confidence
        )
        
        self.knowledge[knowledge_id] = knowledge
        
        # Update index
        for tag in knowledge.tags:
            if tag not in self.index:
                self.index[tag] = set()
            self.index[tag].add(knowledge_id)
        
        logger.info(f"Added knowledge: {knowledge_id}")
        
        if self.storage_path:
            self._save_to_storage()
        
        return knowledge_id
    
    def get_knowledge(self, knowledge_id: str) -> Optional[Knowledge]:
        """
        Get knowledge by ID
        
        Args:
            knowledge_id: Knowledge ID
            
        Returns:
            Knowledge item or None
        """
        return self.knowledge.get(knowledge_id)
    
    def search_knowledge(
        self,
        query: str,
        knowledge_type: Optional[KnowledgeType] = None,
        tags: Optional[Set[str]] = None,
        limit: int = 10
    ) -> List[Knowledge]:
        """
        Search knowledge
        
        Args:
            query: Search query
            knowledge_type: Filter by type
            tags: Filter by tags
            limit: Maximum results
            
        Returns:
            List of knowledge items
        """
        results = []
        
        for knowledge in self.knowledge.values():
            # Type filter
            if knowledge_type and knowledge.type != knowledge_type:
                continue
            
            # Tag filter
            if tags and not tags.issubset(knowledge.tags):
                continue
            
            # Content search
            if query.lower() in knowledge.content.lower():
                results.append(knowledge)
        
        # Sort by confidence
        results.sort(key=lambda k: k.confidence, reverse=True)
        
        return results[:limit]
    
    def update_knowledge(
        self,
        knowledge_id: str,
        content: str = None,
        tags: Set[str] = None,
        metadata: Dict[str, Any] = None,
        confidence: float = None
    ) -> bool:
        """
        Update knowledge
        
        Args:
            knowledge_id: Knowledge ID
            content: New content
            tags: New tags
            metadata: New metadata
            confidence: New confidence
            
        Returns:
            True if updated
        """
        knowledge = self.knowledge.get(knowledge_id)
        
        if not knowledge:
            return False
        
        # Remove old tags from index
        old_tags = knowledge.tags
        for tag in old_tags:
            if tag in self.index:
                self.index[tag].discard(knowledge_id)
        
        # Update knowledge
        if content is not None:
            knowledge.content = content
        if tags is not None:
            knowledge.tags = tags
        if metadata is not None:
            knowledge.metadata = metadata
        if confidence is not None:
            knowledge.confidence = confidence
        
        knowledge.updated_at = time.time()
        
        # Add new tags to index
        for tag in knowledge.tags:
            if tag not in self.index:
                self.index[tag] = set()
            self.index[tag].add(knowledge_id)
        
        if self.storage_path:
            self._save_to_storage()
        
        return True
    
    def delete_knowledge(self, knowledge_id: str) -> bool:
        """
        Delete knowledge
        
        Args:
            knowledge_id: Knowledge ID
            
        Returns:
            True if deleted
        """
        knowledge = self.knowledge.get(knowledge_id)
        
        if not knowledge:
            return False
        
        # Remove from index
        for tag in knowledge.tags:
            if tag in self.index:
                self.index[tag].discard(knowledge_id)
        
        del self.knowledge[knowledge_id]
        
        if self.storage_path:
            self._save_to_storage()
        
        logger.info(f"Deleted knowledge: {knowledge_id}")
        return True
    
    def list_knowledge(
        self,
        knowledge_type: Optional[KnowledgeType] = None,
        tags: Optional[Set[str]] = None,
        limit: int = 100
    ) -> List[Knowledge]:
        """
        List knowledge items
        
        Args:
            knowledge_type: Filter by type
            tags: Filter by tags
            limit: Maximum results
            
        Returns:
            List of knowledge items
        """
        results = []
        
        for knowledge in self.knowledge.values():
            # Type filter
            if knowledge_type and knowledge.type != knowledge_type:
                continue
            
            # Tag filter
            if tags and not tags.issubset(knowledge.tags):
                continue
            
            results.append(knowledge)
        
        return results[:limit]
    
    def get_tags(self) -> Set[str]:
        """Get all tags"""
        return set(self.index.keys())
    
    def get_knowledge_by_tag(self, tag: str) -> List[Knowledge]:
        """
        Get knowledge by tag
        
        Args:
            tag: Tag
            
        Returns:
            List of knowledge items
        """
        knowledge_ids = self.index.get(tag, set())
        return [self.knowledge[kid] for kid in knowledge_ids if kid in self.knowledge]
    
    def validate_knowledge(self, knowledge: Knowledge) -> bool:
        """
        Validate knowledge
        
        Args:
            knowledge: Knowledge item
            
        Returns:
            True if valid
        """
        # Check required fields
        if not knowledge.content or not knowledge.content.strip():
            return False
        
        # Check confidence range
        if not 0 <= knowledge.confidence <= 1:
            return False
        
        return True
    
    def _load_from_storage(self) -> None:
        """Load knowledge from storage"""
        if not self.storage_path:
            return
        
        try:
            path = Path(self.storage_path)
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for item in data:
                    knowledge = Knowledge(
                        id=item["id"],
                        type=KnowledgeType(item["type"]),
                        content=item["content"],
                        metadata=item.get("metadata", {}),
                        tags=set(item.get("tags", [])),
                        confidence=item.get("confidence", 1.0),
                        created_at=item.get("created_at", time.time()),
                        updated_at=item.get("updated_at", time.time())
                    )
                    self.knowledge[knowledge.id] = knowledge
                    
                    # Update index
                    for tag in knowledge.tags:
                        if tag not in self.index:
                            self.index[tag] = set()
                        self.index[tag].add(knowledge.id)
                
                logger.info(f"Loaded {len(self.knowledge)} knowledge items")
        
        except Exception as e:
            logger.error(f"Failed to load knowledge: {e}")
    
    def _save_to_storage(self) -> None:
        """Save knowledge to storage"""
        if not self.storage_path:
            return
        
        try:
            path = Path(self.storage_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            data = []
            for knowledge in self.knowledge.values():
                item = {
                    "id": knowledge.id,
                    "type": knowledge.type.value,
                    "content": knowledge.content,
                    "metadata": knowledge.metadata,
                    "tags": list(knowledge.tags),
                    "confidence": knowledge.confidence,
                    "created_at": knowledge.created_at,
                    "updated_at": knowledge.updated_at
                }
                data.append(item)
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved {len(data)} knowledge items")
        
        except Exception as e:
            logger.error(f"Failed to save knowledge: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        type_counts = {}
        for knowledge in self.knowledge.values():
            ktype = knowledge.type.value
            type_counts[ktype] = type_counts.get(ktype, 0) + 1
        
        return {
            "total_knowledge": len(self.knowledge),
            "total_tags": len(self.index),
            "type_counts": type_counts,
            "storage_path": self.storage_path
        }


class KnowledgeManager:
    """
    Manager for multiple knowledge bases
    
    Provides:
    - Multiple knowledge base management
    - Knowledge sharing
    - Knowledge aggregation
    """
    
    def __init__(self):
        """Initialize knowledge manager"""
        self.knowledge_bases: Dict[str, KnowledgeBase] = {}
    
    def register_knowledge_base(self, name: str, kb: KnowledgeBase) -> None:
        """
        Register a knowledge base
        
        Args:
            name: Knowledge base name
            kb: Knowledge base instance
        """
        self.knowledge_bases[name] = kb
        logger.info(f"Registered knowledge base: {name}")
    
    def get_knowledge_base(self, name: str) -> Optional[KnowledgeBase]:
        """
        Get a knowledge base
        
        Args:
            name: Knowledge base name
            
        Returns:
            Knowledge base or None
        """
        return self.knowledge_bases.get(name)
    
    def search_all(
        self,
        query: str,
        knowledge_type: Optional[KnowledgeType] = None,
        tags: Optional[Set[str]] = None,
        limit: int = 10
    ) -> List[Knowledge]:
        """
        Search all knowledge bases
        
        Args:
            query: Search query
            knowledge_type: Filter by type
            tags: Filter by tags
            limit: Maximum results
            
        Returns:
            List of knowledge items
        """
        results = []
        
        for kb in self.knowledge_bases.values():
            kb_results = kb.search_knowledge(
                query=query,
                knowledge_type=knowledge_type,
                tags=tags,
                limit=limit
            )
            results.extend(kb_results)
        
        # Sort by confidence
        results.sort(key=lambda k: k.confidence, reverse=True)
        
        return results[:limit]


def get_knowledge_base(storage_path: Optional[str] = None) -> KnowledgeBase:
    """Get global knowledge base instance"""
    if not hasattr(get_knowledge_base, "_instance"):
        get_knowledge_base._instance = KnowledgeBase(storage_path)
    return get_knowledge_base._instance


def get_knowledge_manager() -> KnowledgeManager:
    """Get global knowledge manager instance"""
    if not hasattr(get_knowledge_manager, "_instance"):
        get_knowledge_manager._instance = KnowledgeManager()
    return get_knowledge_manager._instance
