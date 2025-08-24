"""Enhanced retriever implementation using query analysis."""

from typing import Dict, List, Optional

from ..embeddings.base import BaseEmbedder
from ..storage_manager.base import BaseStorageManager, SearchResult
from .base import BaseEnhancedRetriever, BaseQueryAnalyzer, BaseHyDEGenerator, AnalysisResult
from .models import RetrievalConfig, RelevanceConfig


class EnhancedRetriever(BaseEnhancedRetriever):
    """Retriever that uses query analysis to improve results."""
    
    def __init__(
        self,
        storage_manager: BaseStorageManager,
        embedder: BaseEmbedder,
        query_analyzer: BaseQueryAnalyzer,
        hyde_generator: Optional[BaseHyDEGenerator] = None,
        relevance_config: Optional[RelevanceConfig] = None
    ):
        """
        Initialize the enhanced retriever.
        
        Args:
            storage_manager: Storage manager for vector operations
            embedder: Embedder for generating query embeddings
            query_analyzer: Query analyzer for intent extraction
            hyde_generator: Optional HyDE generator
        """
        self.storage_manager = storage_manager
        self.embedder = embedder
        self.query_analyzer = query_analyzer
        self.hyde_generator = hyde_generator
        self.relevance_config = relevance_config or RelevanceConfig()
    
    def retrieve(
        self, 
        query: str, 
        limit: int = 5,
        use_hyde: bool = False,
        use_query_expansion: bool = True,
        **kwargs
    ) -> List[SearchResult]:
        """
        Retrieve documents using query analysis.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            use_hyde: Whether to use HyDE for retrieval
            use_query_expansion: Whether to expand the query
            **kwargs: Additional arguments (e.g., filter_metadata)
            
        Returns:
            List of search results
        """
        # Check relevance first if configured
        if self.relevance_config.enabled:
            relevance_result = self.query_analyzer.check_relevance(query)
            
            if relevance_result and not relevance_result.is_relevant:
                print(f"\n⚠️  Query Relevance Check:")
                print(f"  Status: Out of context (confidence: {relevance_result.confidence:.2f})")
                print(f"  Reason: {relevance_result.explanation}")
                
                if self.relevance_config.rejection_mode == "hard":
                    print(f"  Action: Returning no results (hard rejection mode)")
                    if relevance_result.suggestions:
                        print(f"\n  💡 Suggestions:")
                        for suggestion in relevance_result.suggestions:
                            print(f"    - {suggestion}")
                    return []
                elif self.relevance_config.rejection_mode == "soft":
                    print(f"  Action: Proceeding with search anyway (soft rejection mode)")
                    if relevance_result.suggestions:
                        print(f"\n  💡 Suggestions for better results:")
                        for suggestion in relevance_result.suggestions:
                            print(f"    - {suggestion}")
        
        # Get retrieval queries based on configuration
        if use_query_expansion:
            retrieval_queries = self.query_analyzer.get_retrieval_queries(query)
        else:
            retrieval_queries = [query]
        
        print("\n🔍 Query Analysis in Action:")
        print(f"  Original Query: '{query}'")
        print(f"  Expanded to {len(retrieval_queries)} search queries:")
        for i, q in enumerate(retrieval_queries, 1):
            print(f"    {i}. '{q}'")
        
        # Optionally add HyDE
        if use_hyde and self.hyde_generator:
            hypothetical_doc = self.hyde_generator.generate(query)
            retrieval_queries.append(hypothetical_doc)
            print(f"\n  📝 HyDE Generated Document:")
            print(f"    '{hypothetical_doc[:100]}...'")
        
        # Collect all results
        all_results = []
        seen_contents = set()
        
        print(f"\n  🔎 Searching with each query variant:")
        for i, q in enumerate(retrieval_queries, 1):
            # Generate embedding for the query
            query_embedding = self.embedder.embed_text(q).tolist()
            
            # Search with the storage manager
            results = self.storage_manager.search(
                query=q,
                query_embedding=query_embedding,
                limit=limit,
                filter_metadata=kwargs.get('filter_metadata')
            )
            
            new_results = 0
            for result in results:
                # Avoid duplicates based on content
                content_key = result.content[:100]  # Use first 100 chars as key
                if content_key not in seen_contents:
                    seen_contents.add(content_key)
                    all_results.append(result)
                    new_results += 1
            
            print(f"    Query {i}: Found {len(results)} docs, {new_results} new unique")
        
        # Sort by score (highest first) and take top k
        all_results.sort(key=lambda x: x.score, reverse=True)
        final_results = all_results[:limit]
        
        print(f"\n  ✅ Total unique documents found: {len(all_results)}")
        print(f"  📊 Returning top {len(final_results)} documents\n")
        
        return final_results
    
    def retrieve_with_analysis(
        self, 
        query: str, 
        limit: int = 5,
        **kwargs
    ) -> Dict[str, any]:
        """
        Retrieve documents and return analysis details.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            **kwargs: Additional arguments for retrieval
            
        Returns:
            Dictionary containing query analysis and search results
        """
        # Analyze query
        intent = self.query_analyzer.analyze(query)
        
        # Add relevance warning if applicable
        if intent.relevance_info and not intent.relevance_info.is_relevant:
            print(f"\n⚠️  Note: This query appears to be outside the domain context")
            print(f"  Confidence: {intent.relevance_info.confidence:.2f}")
            print(f"  Consider refining your query for better results")
        
        # Get retrieval queries
        retrieval_queries = self.query_analyzer.get_retrieval_queries(query)
        
        # Perform retrieval
        results = self.retrieve(
            query=query,
            limit=limit,
            **kwargs
        )
        
        # Create analysis result
        analysis = AnalysisResult(
            query=query,
            intent=intent,
            retrieval_queries=retrieval_queries,
            hypothetical_document=None
        )
        
        # Add HyDE document if used
        if kwargs.get('use_hyde', False) and self.hyde_generator:
            analysis.hypothetical_document = self.hyde_generator.generate(query)
        
        return {
            "query": analysis.query,
            "intent": {
                "query_type": analysis.intent.query_type,
                "entities": analysis.intent.entities,
                "time_filter": analysis.intent.time_filter,
                "semantic_intent": analysis.intent.semantic_intent,
                "expanded_queries": analysis.intent.expanded_queries,
                "relevance_info": {
                    "is_relevant": analysis.intent.relevance_info.is_relevant if analysis.intent.relevance_info else True,
                    "confidence": analysis.intent.relevance_info.confidence if analysis.intent.relevance_info else 1.0,
                    "stage": analysis.intent.relevance_info.stage if analysis.intent.relevance_info else None,
                    "explanation": analysis.intent.relevance_info.explanation if analysis.intent.relevance_info else None
                } if analysis.intent.relevance_info else None
            },
            "retrieval_queries": analysis.retrieval_queries,
            "hypothetical_document": analysis.hypothetical_document,
            "results": [
                {
                    "content": result.content,
                    "metadata": {
                        "title": result.metadata.title,
                        "page_number": result.metadata.page_number,
                        "section_path": result.metadata.section_path
                    },
                    "score": result.score,
                    "image_paths": result.image_paths
                }
                for result in results
            ]
        }
    
    def retrieve_with_config(self, query: str, config: RetrievalConfig) -> List[SearchResult]:
        """
        Retrieve documents using a configuration object.
        
        Args:
            query: The search query
            config: Retrieval configuration
            
        Returns:
            List of search results
        """
        return self.retrieve(
            query=query,
            limit=config.limit,
            use_hyde=config.use_hyde,
            use_query_expansion=config.use_query_expansion,
            filter_metadata=config.filter_metadata
        )