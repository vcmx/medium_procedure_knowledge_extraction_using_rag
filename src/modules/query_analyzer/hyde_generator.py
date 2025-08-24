"""HyDE (Hypothetical Document Embeddings) generator implementations."""

from typing import Optional

from .base import BaseHyDEGenerator
from .models import HyDEConfig


class OllamaHyDEGenerator(BaseHyDEGenerator):
    """HyDE generator using Ollama for local LLM inference."""
    
    def __init__(self, config: Optional[HyDEConfig] = None):
        """Initialize the HyDE generator."""
        self.config = config or HyDEConfig()
        
        # Lazy import to make Ollama optional
        try:
            from langchain_ollama import ChatOllama
            from langchain_core.prompts import ChatPromptTemplate
        except ImportError:
            raise ImportError(
                "Ollama dependencies not installed. "
                "Please install with: pip install langchain-ollama"
            )
        
        self.llm = ChatOllama(
            model=self.config.model_name,
            temperature=self.config.temperature
        )
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at generating hypothetical documents.
Given a user query, generate a short document (2-3 sentences) that would perfectly answer their question.
This document should contain the key information they're looking for.
The document should be factual and informative, as if it were an excerpt from a technical manual or textbook."""),
            ("human", "Query: {query}\n\nHypothetical answer document:")
        ])
        
        self.chain = self.prompt | self.llm
    
    def generate(self, query: str) -> str:
        """Generate a hypothetical document that would answer the query."""
        response = self.chain.invoke({"query": query})
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Truncate if too long
        if len(content) > self.config.max_length:
            content = content[:self.config.max_length].rsplit(' ', 1)[0] + "..."
        
        return content


class OpenRouterHyDEGenerator(BaseHyDEGenerator):
    """HyDE generator using OpenRouter API."""
    
    def __init__(self, config: Optional[HyDEConfig] = None):
        """Initialize the HyDE generator."""
        self.config = config or HyDEConfig()
        
        if not self.config.openrouter_api_key:
            raise ValueError("OpenRouter API key is required for OpenRouterHyDEGenerator")
        
        # Implementation would use OpenRouter API
        # This is a placeholder - actual implementation would depend on
        # how OpenRouter is integrated in the target project
        raise NotImplementedError("OpenRouter integration not yet implemented")
    
    def generate(self, query: str) -> str:
        """Generate a hypothetical document using OpenRouter."""
        # Placeholder for OpenRouter implementation
        raise NotImplementedError("OpenRouter integration not yet implemented")