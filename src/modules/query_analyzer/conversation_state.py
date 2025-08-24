"""Conversation state management for multi-turn query processing."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from datetime import datetime
from enum import Enum

from .base import QueryIntent


class UserLevel(Enum):
    """User expertise level for adaptive responses."""
    NOVICE = "novice"
    EXPERIENCED = "experienced"
    EXPERT = "expert"


@dataclass
class ClarificationRecord:
    """Record of a clarification interaction."""
    question: str
    answer: str
    timestamp: datetime
    query_context: str


@dataclass
class ConversationTurn:
    """Represents a single turn in the conversation."""
    query: str
    intent: Optional[QueryIntent]
    clarifications: List[ClarificationRecord]
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationState:
    """Maintains state across conversation turns."""
    
    session_id: str
    created_at: datetime
    updated_at: datetime
    
    # Conversation history
    turns: List[ConversationTurn] = field(default_factory=list)
    
    # Accumulated context
    entities_mentioned: Set[str] = field(default_factory=set)
    topics_discussed: List[str] = field(default_factory=list)
    clarifications_made: Dict[str, str] = field(default_factory=dict)
    
    # User context
    user_level: UserLevel = UserLevel.NOVICE
    preferences: Dict[str, Any] = field(default_factory=dict)
    
    # Current conversation context
    current_domain: Optional[str] = None
    current_task_type: Optional[str] = None
    
    def add_turn(self, query: str, intent: Optional[QueryIntent] = None, 
                 clarifications: Optional[List[ClarificationRecord]] = None) -> None:
        """Add a conversation turn to the history."""
        turn = ConversationTurn(
            query=query,
            intent=intent,
            clarifications=clarifications or [],
            timestamp=datetime.now()
        )
        self.turns.append(turn)
        self.updated_at = datetime.now()
        
        # Update accumulated context
        if intent:
            self.entities_mentioned.update(intent.entities)
            if intent.semantic_intent not in self.topics_discussed:
                self.topics_discussed.append(intent.semantic_intent)
    
    def add_clarification(self, question: str, answer: str, query_context: str) -> None:
        """Record a clarification interaction."""
        record = ClarificationRecord(
            question=question,
            answer=answer,
            timestamp=datetime.now(),
            query_context=query_context
        )
        
        if self.turns:
            self.turns[-1].clarifications.append(record)
        
        self.clarifications_made[question] = answer
        self.updated_at = datetime.now()
    
    def get_recent_context(self, n_turns: int = 3) -> List[ConversationTurn]:
        """Get the most recent n conversation turns."""
        return self.turns[-n_turns:] if self.turns else []
    
    def get_all_entities(self) -> Set[str]:
        """Get all entities mentioned in the conversation."""
        return self.entities_mentioned.copy()
    
    def get_clarification_history(self) -> Dict[str, str]:
        """Get all clarifications made during the conversation."""
        return self.clarifications_made.copy()
    
    def update_user_level(self, level: UserLevel) -> None:
        """Update the user's expertise level."""
        self.user_level = level
        self.updated_at = datetime.now()
    
    def set_preference(self, key: str, value: Any) -> None:
        """Set a user preference."""
        self.preferences[key] = value
        self.updated_at = datetime.now()
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get a summary of the conversation state."""
        return {
            "session_id": self.session_id,
            "turn_count": len(self.turns),
            "entities_mentioned": list(self.entities_mentioned),
            "topics_discussed": self.topics_discussed,
            "clarification_count": len(self.clarifications_made),
            "user_level": self.user_level.value,
            "current_domain": self.current_domain,
            "current_task_type": self.current_task_type,
            "duration_seconds": (self.updated_at - self.created_at).total_seconds()
        }
    
    def build_context_prompt(self) -> str:
        """Build a context prompt for the analyzer based on conversation history."""
        if not self.turns:
            return ""
        
        context_parts = []
        
        # Add recent conversation history
        recent_turns = self.get_recent_context(3)
        if recent_turns:
            context_parts.append("Recent conversation:")
            for turn in recent_turns:
                context_parts.append(f"- User: {turn.query}")
                if turn.intent:
                    context_parts.append(f"  Intent: {turn.intent.semantic_intent}")
        
        # Add entities mentioned
        if self.entities_mentioned:
            context_parts.append(f"\nEntities discussed: {', '.join(self.entities_mentioned)}")
        
        # Add clarifications
        if self.clarifications_made:
            context_parts.append("\nClarifications made:")
            for q, a in list(self.clarifications_made.items())[-3:]:  # Last 3 clarifications
                context_parts.append(f"- Q: {q}")
                context_parts.append(f"  A: {a}")
        
        # Add domain context
        if self.current_domain:
            context_parts.append(f"\nCurrent domain: {self.current_domain}")
        
        if self.current_task_type:
            context_parts.append(f"Task type: {self.current_task_type}")
        
        context_parts.append(f"User level: {self.user_level.value}")
        
        return "\n".join(context_parts)
    
    def should_clarify(self, confidence_threshold: float = 0.7) -> bool:
        """Determine if clarification is needed based on conversation history."""
        # If we've already clarified a lot, be more selective
        if len(self.clarifications_made) > 5:
            return False
        
        # If this is the first turn, more likely to need clarification
        if len(self.turns) <= 1:
            return True
        
        # Check if recent intents had low confidence
        recent_turns = self.get_recent_context(2)
        for turn in recent_turns:
            if turn.intent and hasattr(turn.intent, 'confidence'):
                if turn.intent.confidence < confidence_threshold:
                    return True
        
        return False