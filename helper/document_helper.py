from typing import Annotated, TypedDict, Sequence, Optional, Literal
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import logging

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import os
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('drafter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DocumentType(Enum):
    """Enum for document types - more maintainable than strings"""
    RESUME = "resume"
    COVER_LETTER = "cover_letter"

@dataclass
class AgentConfig:
    """Centralized configuration - easier to test and modify"""
    model_name: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    temperature: float = 0.5
    max_tokens: int = 500
    output_dir: Path = field(default_factory=lambda: Path("./outputs"))
    
    def __post_init__(self):
        self.output_dir.mkdir(exist_ok=True)

@dataclass
class DocumentMetadata:
    """Track document versioning and history"""
    content: str
    created_at: datetime
    last_modified: datetime
    version: int = 1
    word_count: int = 0
    
    def __post_init__(self):
        self.word_count = len(self.content.split())


class DocumentStore:
    """
    Encapsulated state management - no more globals!
    Supports versioning, history, and persistence
    """
    def __init__(self):
        self._documents: dict[DocumentType, DocumentMetadata] = {}
        self._history: list[tuple[DocumentType, str]] = []
    
    def create(self, doc_type: DocumentType, content: str) -> DocumentMetadata:
        """Create or update a document with versioning"""
        now = datetime.now()
        
        if doc_type in self._documents:
            # Update existing document
            prev = self._documents[doc_type]
            metadata = DocumentMetadata(
                content=content,
                created_at=prev.created_at,
                last_modified=now,
                version=prev.version + 1
            )
        else:
            # Create new document
            metadata = DocumentMetadata(
                content=content,
                created_at=now,
                last_modified=now
            )
        
        self._documents[doc_type] = metadata
        self._history.append((doc_type, content))
        logger.info(f"Created/updated {doc_type.value} v{metadata.version}")
        return metadata
    
    def get(self, doc_type: DocumentType) -> Optional[DocumentMetadata]:
        """Retrieve document if exists"""
        return self._documents.get(doc_type)
    
    def exists(self, doc_type: DocumentType) -> bool:
        """Check if document exists"""
        return doc_type in self._documents
    
    def get_history(self, doc_type: DocumentType) -> list[str]:
        """Get version history for a document"""
        return [content for dt, content in self._history if dt == doc_type]
    
    def clear(self):
        """Reset all documents"""
        self._documents.clear()
        self._history.clear()