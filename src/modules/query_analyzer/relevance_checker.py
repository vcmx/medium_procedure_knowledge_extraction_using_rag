"""Contextual relevance checker for query analysis."""

import json
import re
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
import numpy as np
from dataclasses import dataclass

from .models import RelevanceResult, RelevanceConfig
from ..embeddings.base import BaseEmbedder


class ContextualRelevanceChecker:
    """Two-stage relevance checker for determining if queries are within domain context."""
    
    def __init__(self, config: RelevanceConfig, embedder: Optional[BaseEmbedder] = None, llm_provider: Optional[Any] = None):
        """
        Initialize the relevance checker.
        
        Args:
            config: Configuration for relevance checking
            embedder: Optional embedder for semantic validation
            llm_provider: Optional LLM provider for task-action-target evaluation
        """
        self.config = config
        self.embedder = embedder
        self.llm_provider = llm_provider
        
        # Load domain knowledge
        self.domain_vocabulary = self._load_domain_vocabulary()
        self.domain_patterns = self._compile_patterns()
        self.representative_embeddings = None  # Lazy loaded
        
        # Cache for performance
        self._query_cache = {}
        
    def check_relevance(self, query: str) -> RelevanceResult:
        """
        Check if a query is contextually relevant to the domain.
        
        The evaluation method is determined by config.evaluation_mode:
        - "two_stage" (default): Uses vocabulary/pattern matching + semantic validation
        - "task_action_target": Checks for presence of action verbs and target objects
        
        Args:
            query: The user query to check
            
        Returns:
            RelevanceResult with relevance determination
            
        Examples:
            >>> # Two-stage mode
            >>> config = RelevanceConfig(evaluation_mode="two_stage")
            >>> checker = ContextualRelevanceChecker(config)
            >>> result = checker.check_relevance("What is the torque specification?")
            >>> print(result.stage)  # "pre-filter" or "semantic"
            
            >>> # Task-action-target mode
            >>> config = RelevanceConfig(evaluation_mode="task_action_target")
            >>> checker = ContextualRelevanceChecker(config)
            >>> result = checker.check_relevance("remove the oil filter")
            >>> print(result.stage)  # "task-action-target"
        """
        # Check cache first
        if query in self._query_cache:
            return self._query_cache[query]
        
        # Check evaluation mode
        if self.config.evaluation_mode == "task_action_target":
            # Use task-action-target evaluation with LLM
            if not self.llm_provider:
                # Fallback to rule-based if no LLM provided
                result = self._check_task_action_target_fallback(query)
            else:
                result = self.check_task_action_target(query)
            self._query_cache[query] = result
            return result
        
        # Default: two-stage evaluation
        # Stage 1: Fast pre-filter
        pre_filter_result = self._fast_prefilter(query)
        
        # If clearly relevant or irrelevant, return early
        if pre_filter_result.confidence >= self.config.high_confidence_threshold:
            self._query_cache[query] = pre_filter_result
            return pre_filter_result
            
        if pre_filter_result.confidence <= self.config.low_confidence_threshold:
            self._query_cache[query] = pre_filter_result
            return pre_filter_result
            
        # Stage 2: Semantic validation (if configured and embedder available)
        if self.config.enable_semantic_validation and self.embedder:
            semantic_result = self._semantic_validation(query, pre_filter_result)
            self._query_cache[query] = semantic_result
            return semantic_result
            
        # Return pre-filter result if semantic validation not available
        self._query_cache[query] = pre_filter_result
        return pre_filter_result
    
    def _fast_prefilter(self, query: str) -> RelevanceResult:
        """
        Fast pre-filtering based on domain vocabulary and patterns.
        
        Args:
            query: The query to check
            
        Returns:
            RelevanceResult from pre-filtering
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        # Check 1: Domain vocabulary matching
        domain_matches = self._find_domain_terms(query_lower, query_words)
        vocab_score = self._calculate_vocab_score(domain_matches, len(query_words))
        
        # Check 2: Pattern matching (regex for technical patterns)
        pattern_matches = self._find_pattern_matches(query)
        pattern_score = min(len(pattern_matches) * 0.2, 0.4)  # Cap at 0.4
        
        # Check 3: Query type indicators
        type_score = self._check_query_type_indicators(query_lower)
        
        # Check 4: Negative indicators (out-of-domain clues)
        negative_score = self._check_negative_indicators(query_lower)
        
        # Combine scores
        total_score = max(0, min(1.0, vocab_score + pattern_score + type_score - negative_score))
        
        # Determine relevance
        is_relevant = total_score >= self.config.low_confidence_threshold
        
        # Generate explanation
        explanation = self._generate_explanation(
            domain_matches, pattern_matches, type_score, negative_score, total_score
        )
        
        # Apply rejection mode logic
        final_is_relevant = is_relevant
        if not is_relevant:
            if self.config.rejection_mode == "soft":
                # In soft mode, allow processing with low confidence warning
                final_is_relevant = True
                explanation = f"⚠️ Low confidence warning: {explanation}"
            elif self.config.rejection_mode == "score":
                # In score mode, never reject - always continue
                final_is_relevant = True
            # Hard mode keeps original is_relevant=False
        
        return RelevanceResult(
            is_relevant=final_is_relevant,
            confidence=total_score,
            stage="pre-filter",
            explanation=explanation,
            domain_matches=[match for matches in domain_matches.values() for match in matches],
            suggestions=self._generate_suggestions(query) if not final_is_relevant else None
        )
    
    def _semantic_validation(self, query: str, pre_filter_result: RelevanceResult) -> RelevanceResult:
        """
        Semantic validation using embeddings.
        
        Args:
            query: The query to validate
            pre_filter_result: Result from pre-filtering
            
        Returns:
            RelevanceResult from semantic validation
        """
        # Load representative embeddings if not already loaded
        if self.representative_embeddings is None:
            self._load_representative_embeddings()
            
        if not self.representative_embeddings:
            # Fall back to pre-filter if no embeddings available
            return pre_filter_result
        
        # Get query embedding
        query_embedding = self.embedder.embed_text(query)
        
        # Calculate similarities
        similarities = []
        for category, embeddings in self.representative_embeddings.items():
            category_sims = []
            for rep_emb in embeddings:
                similarity = self._cosine_similarity(query_embedding, rep_emb)
                category_sims.append(similarity)
                
            similarities.append({
                'category': category,
                'max_similarity': max(category_sims) if category_sims else 0,
                'avg_similarity': sum(category_sims) / len(category_sims) if category_sims else 0
            })
        
        # Determine relevance based on maximum similarity
        max_sim = max(s['max_similarity'] for s in similarities) if similarities else 0
        is_relevant = max_sim >= self.config.semantic_threshold
        
        # Find best matching category
        best_category = max(similarities, key=lambda x: x['max_similarity'])['category'] if similarities else "unknown"
        
        # Adjust confidence based on both stages
        combined_confidence = (pre_filter_result.confidence + max_sim) / 2
        
        explanation = (
            f"Semantic validation: {max_sim:.2f} similarity to '{best_category}' category. "
            f"Combined with pre-filter confidence: {combined_confidence:.2f}"
        )
        
        # Apply rejection mode logic
        final_is_relevant = is_relevant
        if not is_relevant:
            if self.config.rejection_mode == "soft":
                # In soft mode, allow processing with low confidence warning
                final_is_relevant = True
                explanation = f"⚠️ Low confidence warning: {explanation}"
            elif self.config.rejection_mode == "score":
                # In score mode, never reject - always continue
                final_is_relevant = True
            # Hard mode keeps original is_relevant=False
        
        return RelevanceResult(
            is_relevant=final_is_relevant,
            confidence=combined_confidence,
            stage="semantic",
            explanation=explanation,
            domain_matches=pre_filter_result.domain_matches,
            suggestions=self._generate_suggestions(query) if not final_is_relevant else None
        )
    
    def _find_domain_terms(self, query_lower: str, query_words: Set[str]) -> Dict[str, List[str]]:
        """Find domain vocabulary terms in the query."""
        matches = {}
        
        for category, terms in self.domain_vocabulary.items():
            category_matches = []
            for term in terms:
                term_lower = term.lower()
                # Check exact word match or substring match for multi-word terms
                if ' ' in term_lower:
                    if term_lower in query_lower:
                        category_matches.append(term)
                elif term_lower in query_words:
                    category_matches.append(term)
                    
            if category_matches:
                matches[category] = category_matches
                
        return matches
    
    def _calculate_vocab_score(self, domain_matches: Dict[str, List[str]], query_word_count: int) -> float:
        """Calculate vocabulary matching score."""
        if not domain_matches or query_word_count == 0:
            return 0.0
            
        # Weight different categories
        weighted_score = 0.0
        category_weights = {
            'technical_terms': 0.3,
            'component_names': 0.3,
            'actions': 0.2,
            'measurements': 0.2
        }
        
        for category, matches in domain_matches.items():
            weight = category_weights.get(category, 0.1)
            weighted_score += len(matches) * weight
            
        # Normalize by query length
        normalized_score = min(weighted_score / max(query_word_count * 0.3, 1), 1.0)
        
        return normalized_score
    
    def _find_pattern_matches(self, query: str) -> List[Tuple[str, str]]:
        """Find technical pattern matches in the query."""
        matches = []
        
        for pattern_name, pattern in self.domain_patterns.items():
            found = pattern.findall(query)
            if found:
                matches.extend([(pattern_name, match) for match in found])
                
        return matches
    
    def _check_query_type_indicators(self, query_lower: str) -> float:
        """Check for query type indicators that suggest technical context."""
        technical_indicators = [
            'how to', 'how do i', 'what is the', 'where is',
            'procedure', 'specification', 'torque', 'clearance',
            'install', 'remove', 'replace', 'inspect', 'adjust',
            'troubleshoot', 'diagnose', 'repair', 'maintenance'
        ]
        
        score = 0.0
        for indicator in technical_indicators:
            if indicator in query_lower:
                score += 0.1
                
        return min(score, 0.3)  # Cap at 0.3
    
    def _check_negative_indicators(self, query_lower: str) -> float:
        """Check for indicators that suggest out-of-domain queries."""
        negative_indicators = [
            'weather', 'news', 'sports', 'movie', 'song', 'recipe',
            'joke', 'story', 'poem', 'game', 'social media',
            'facebook', 'twitter', 'instagram', 'tiktok'
        ]
        
        score = 0.0
        for indicator in negative_indicators:
            if indicator in query_lower:
                score += 0.3
                
        return min(score, 0.9)  # Cap at 0.9
    
    def _generate_explanation(
        self, 
        domain_matches: Dict[str, List[str]], 
        pattern_matches: List[Tuple[str, str]],
        type_score: float,
        negative_score: float,
        total_score: float
    ) -> str:
        """Generate a human-readable explanation of the relevance check."""
        parts = []
        
        if domain_matches:
            terms = [term for matches in domain_matches.values() for term in matches]
            parts.append(f"Found domain terms: {', '.join(terms[:3])}")
            
        if pattern_matches:
            parts.append(f"Matched {len(pattern_matches)} technical patterns")
            
        if type_score > 0:
            parts.append("Contains technical query indicators")
            
        if negative_score > 0:
            parts.append("Contains out-of-domain indicators")
            
        if not parts:
            parts.append("No clear domain indicators found")
            
        return f"{'; '.join(parts)} (confidence: {total_score:.2f})"
    
    def _generate_suggestions(self, query: str) -> List[str]:
        """Generate suggestions for making the query more relevant."""
        suggestions = []
        
        # Generic suggestions
        suggestions.append("Try including specific component names or part numbers")
        suggestions.append("Mention the specific system or procedure you're asking about")
        
        # Check if query is too short
        if len(query.split()) < 3:
            suggestions.append("Provide more context or details in your question")
            
        return suggestions[:3]  # Return top 3 suggestions
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return float(dot_product / (norm1 * norm2))
    
    def _load_domain_vocabulary(self) -> Dict[str, List[str]]:
        """Load domain vocabulary from file."""
        vocab_path = Path(self.config.domain_vocabulary_path)
        
        if not vocab_path.exists():
            # Return default vocabulary for automotive domain
            return {
                "technical_terms": [
                    "engine", "transmission", "brake", "suspension", "steering",
                    "cooling system", "exhaust", "fuel system", "electrical",
                    "hydraulic", "pneumatic", "diagnostic", "calibration"
                ],
                "component_names": [
                    "cylinder", "piston", "valve", "gear", "bearing", "seal",
                    "gasket", "filter", "pump", "sensor", "actuator", "module",
                    "belt", "chain", "pulley", "shaft", "rotor", "caliper"
                ],
                "actions": [
                    "install", "remove", "replace", "inspect", "adjust",
                    "torque", "align", "calibrate", "test", "measure",
                    "clean", "lubricate", "tighten", "loosen", "check"
                ],
                "measurements": [
                    "torque", "pressure", "temperature", "clearance", "gap",
                    "voltage", "resistance", "current", "flow rate", "rpm",
                    "angle", "dimension", "tolerance", "specification"
                ]
            }
            
        with open(vocab_path, 'r') as f:
            return json.load(f)
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for technical content."""
        patterns_path = Path(self.config.domain_patterns_path)
        
        if not patterns_path.exists():
            # Return default patterns
            pattern_strings = {
                "part_number": r'[A-Z0-9]{2,}-[A-Z0-9]{2,}(?:-[A-Z0-9]+)*',
                "measurement": r'\d+\.?\d*\s*(mm|cm|m|km|in|ft|psi|bar|kPa|MPa|°C|°F|K|lb|kg|g|N|Nm|ft-lb)',
                "reference": r'(?:figure|table|section|step|page)\s+\d+(?:\.\d+)*',
                "specification": r'\d+\.?\d*\s*(?:±|to|-)\s*\d+\.?\d*\s*(?:mm|cm|psi|bar|°C|°F)',
                "model_year": r'(?:19|20)\d{2}\s*(?:model|year|MY)?'
            }
        else:
            with open(patterns_path, 'r') as f:
                pattern_strings = json.load(f)
                
        # Compile patterns
        compiled_patterns = {}
        for name, pattern in pattern_strings.items():
            try:
                compiled_patterns[name] = re.compile(pattern, re.IGNORECASE)
            except re.error:
                print(f"Warning: Invalid regex pattern for '{name}': {pattern}")
                
        return compiled_patterns
    
    def _load_representative_embeddings(self):
        """Load representative embeddings for semantic validation."""
        embeddings_path = Path(self.config.representative_embeddings_path)
        
        if embeddings_path.exists():
            try:
                with open(embeddings_path, 'rb') as f:
                    self.representative_embeddings = pickle.load(f)
            except Exception as e:
                print(f"Warning: Could not load representative embeddings: {e}")
                self.representative_embeddings = {}
        else:
            # Initialize with empty dict - will be populated during system use
            self.representative_embeddings = {}
    
    def update_representative_embeddings(self, category: str, embedding: np.ndarray):
        """
        Update representative embeddings with a new example.
        
        Args:
            category: Category name for the embedding
            embedding: The embedding vector to add
        """
        if self.representative_embeddings is None:
            self.representative_embeddings = {}
            
        if category not in self.representative_embeddings:
            self.representative_embeddings[category] = []
            
        # Add embedding (limit to max 10 per category to manage size)
        self.representative_embeddings[category].append(embedding)
        if len(self.representative_embeddings[category]) > 10:
            # Keep only the most recent 10
            self.representative_embeddings[category] = self.representative_embeddings[category][-10:]
            
        # Optionally save to disk
        if self.config.representative_embeddings_path:
            embeddings_path = Path(self.config.representative_embeddings_path)
            with open(embeddings_path, 'wb') as f:
                pickle.dump(self.representative_embeddings, f)
    
    def check_task_action_target(self, query: str) -> RelevanceResult:
        """
        Check relevance using LLM-based task-action-target evaluation.
        
        Uses the technical_tasks_evaluate.txt prompt to evaluate if the query
        contains essential technical task components via LLM analysis.
        
        Args:
            query: The user query to check
            
        Returns:
            RelevanceResult with LLM-based task-action-target evaluation
            
        Examples:
            >>> checker = ContextualRelevanceChecker(config, llm_provider=llm)
            >>> result = checker.check_task_action_target("remove the oil filter")
            >>> print(result.is_relevant)  # True
            >>> print(result.confidence)   # 1.0
            >>> print(result.stage)        # "task-action-target"
        """
        if not self.llm_provider:
            raise ValueError("LLM provider required for task-action-target evaluation mode")
        
        # Load prompt template
        prompt_template = self._load_task_action_prompt()
        
        # Format prompt with query
        formatted_prompt = prompt_template.replace("{query}", query)
        
        try:
            # Get LLM response
            response = self._query_llm(formatted_prompt)
            
            # Parse LLM response to create RelevanceResult
            return self._parse_llm_response(response, query)
            
        except Exception as e:
            # Fallback to rule-based evaluation on error
            print(f"Warning: LLM evaluation failed ({e}), falling back to rule-based evaluation")
            return self._check_task_action_target_fallback(query)
    
    def _load_task_action_prompt(self) -> str:
        """Load the task-action-target evaluation prompt template."""
        prompt_path = Path(self.config.task_action_prompt_path)
        if not prompt_path.exists():
            raise FileNotFoundError(f"Task action prompt file not found: {prompt_path}")
        
        with open(prompt_path, 'r') as f:
            return f.read()
    
    def _query_llm(self, prompt: str) -> str:
        """Query the LLM with the formatted prompt."""
        # The LLM provider should be compatible with langchain interface
        if hasattr(self.llm_provider, 'invoke'):
            # Langchain-style interface
            response = self.llm_provider.invoke(prompt)
            if hasattr(response, 'content'):
                return response.content
            return str(response)
        else:
            # Fallback for other interfaces
            return self.llm_provider(prompt)
    
    def _parse_llm_response(self, response: str, original_query: str) -> RelevanceResult:
        """
        Parse LLM response and extract RelevanceResult components.
        
        The LLM should follow the structured format specified in technical_tasks_evaluate.txt.
        """
        try:
            lines = response.strip().split('\n')
            
            # Initialize default values
            is_relevant = False
            confidence = 0.0
            actions_found = []
            targets_found = []
            explanation = ""
            suggestions = []
            
            # Parse each line looking for the structured format
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('RELEVANT:'):
                    value = line.split(':', 1)[1].strip()
                    is_relevant = value.lower() == 'true'
                    
                elif line.startswith('CONFIDENCE:'):
                    value = line.split(':', 1)[1].strip()
                    try:
                        confidence = float(value)
                    except ValueError:
                        confidence = 0.5
                        
                elif line.startswith('ACTIONS_FOUND:'):
                    value = line.split(':', 1)[1].strip()
                    if value.lower() != 'none':
                        # Split by comma and clean up, remove brackets
                        actions_found = [action.strip().strip('[]') for action in value.split(',') if action.strip()]
                        
                elif line.startswith('TARGETS_FOUND:'):
                    value = line.split(':', 1)[1].strip()
                    if value.lower() != 'none':
                        # Split by comma and clean up, remove brackets
                        targets_found = [target.strip().strip('[]') for target in value.split(',') if target.strip()]
                        
                elif line.startswith('EXPLANATION:'):
                    explanation = line.split(':', 1)[1].strip()
                    
                elif line.startswith('SUGGESTIONS:'):
                    value = line.split(':', 1)[1].strip()
                    if value.lower() != 'none':
                        # Split by semicolon for multiple suggestions
                        suggestions = [s.strip() for s in value.split(';') if s.strip()]
            
            # Create domain matches from actions and targets
            domain_matches = []
            for action in actions_found:
                domain_matches.append(f"action:{action}")
            for target in targets_found:
                domain_matches.append(f"target:{target}")
            
            # Apply rejection mode logic
            final_is_relevant = is_relevant
            if not is_relevant:
                if self.config.rejection_mode == "soft":
                    # In soft mode, allow processing with low confidence warning
                    final_is_relevant = True
                    explanation = f"⚠️ Low confidence warning: {explanation}"
                elif self.config.rejection_mode == "score":
                    # In score mode, never reject - always continue
                    final_is_relevant = True
                # Hard mode keeps original is_relevant=False
            
            # Use suggestions only if not relevant in final result
            final_suggestions = suggestions if not final_is_relevant and suggestions else None
            
            return RelevanceResult(
                is_relevant=final_is_relevant,
                confidence=confidence,
                stage="task-action-target",
                explanation=explanation or "LLM evaluation completed",
                domain_matches=domain_matches,
                suggestions=final_suggestions[:3] if final_suggestions else None
            )
            
        except Exception as e:
            # Fallback parsing if structured parsing fails
            print(f"Warning: Failed to parse structured LLM response ({e}), using fallback parsing")
            
            response_lower = response.lower()
            is_relevant = "relevant: true" in response_lower or "true" in response_lower
            
            # Try to extract confidence
            confidence = 0.5
            import re
            conf_match = re.search(r'confidence[:\s]*([0-9]*\.?[0-9]+)', response_lower)
            if conf_match:
                try:
                    confidence = float(conf_match.group(1))
                except ValueError:
                    pass
            
            return RelevanceResult(
                is_relevant=is_relevant,
                confidence=confidence,
                stage="task-action-target",
                explanation=f"LLM response: {response[:200]}..." if len(response) > 200 else response,
                domain_matches=[],
                suggestions=["Please rephrase your query with clear action and target"] if not is_relevant else None
            )
    
    def _check_task_action_target_fallback(self, query: str) -> RelevanceResult:
        """
        Fallback rule-based task-action-target evaluation when LLM is not available.
        
        This is the original implementation for backward compatibility.
        """
        query_lower = query.lower()
        query_words = query_lower.split()
        
        # Load domain vocabulary if not already loaded
        if not hasattr(self, '_task_actions') or not hasattr(self, '_target_objects'):
            self._load_task_action_vocabulary()
        
        # Find task actions and target objects
        found_actions = []
        found_targets = []
        
        # Check for actions
        for word in query_words:
            if word in self._task_actions:
                found_actions.append(word)
        
        # Check for targets (including multi-word targets)
        for target in self._target_objects:
            if target.lower() in query_lower:
                found_targets.append(target)
        
        # Calculate confidence
        has_action = len(found_actions) > 0
        has_target = len(found_targets) > 0
        
        if has_action and has_target:
            confidence = 1.0
            is_relevant = True
            explanation = f"Rule-based: Found action '{found_actions[0]}' and target '{found_targets[0]}'"
        elif has_action and not has_target:
            confidence = 0.5
            is_relevant = False
            explanation = f"Rule-based: Found action '{found_actions[0]}' but missing target"
        elif not has_action and has_target:
            confidence = 0.3
            is_relevant = False
            explanation = f"Rule-based: Found target '{found_targets[0]}' but missing action"
        else:
            confidence = 0.0
            is_relevant = False
            explanation = "Rule-based: No technical action or equipment found"
        
        # Format domain matches
        domain_matches = []
        for action in found_actions:
            domain_matches.append(f"action:{action}")
        for target in found_targets:
            domain_matches.append(f"target:{target}")
        
        # Generate suggestions
        suggestions = None
        if not is_relevant:
            suggestions = []
            if not has_action:
                suggestions.append("Specify what you want to do (e.g., 'remove', 'install', 'adjust')")
            if not has_target:
                suggestions.append("Specify the component (e.g., 'brake pads', 'oil filter', 'spark plug')")
        
        return RelevanceResult(
            is_relevant=is_relevant,
            confidence=confidence,
            stage="task-action-target",
            explanation=explanation,
            domain_matches=domain_matches,
            suggestions=suggestions[:3] if suggestions else None
        )
    
    def _load_task_action_vocabulary(self):
        """
        Load task actions and target objects from domain vocabulary.
        
        This method populates two sets:
        - _task_actions: Technical verbs like "remove", "install", "adjust"
        - _target_objects: Equipment/component names like "filter", "engine", "bolt"
        
        The vocabulary is loaded from the domain vocabulary file and extended
        with additional common technical terms.
        """
        # Try to load from domain vocabulary first
        vocab = self._load_domain_vocabulary()
        
        # Extract actions from vocabulary
        self._task_actions = set()
        if 'actions' in vocab:
            self._task_actions.update(word.lower() for word in vocab['actions'])
        
        # Add additional common technical actions
        self._task_actions.update([
            'remove', 'install', 'replace', 'inspect', 'adjust', 'tighten', 'loosen',
            'align', 'calibrate', 'test', 'measure', 'clean', 'lubricate', 'check',
            'mount', 'dismount', 'service', 'repair', 'diagnose', 'troubleshoot',
            'unscrew', 'screw', 'shift', 'cover', 'mark', 'drain', 'fill', 'bleed'
        ])
        
        # Extract targets from vocabulary
        self._target_objects = set()
        if 'component_names' in vocab:
            self._target_objects.update(vocab['component_names'])
        
        # Add additional common technical objects
        self._target_objects.update([
            'screw', 'nut', 'bolt', 'cover', 'pipe', 'shaft', 'cam', 'piston',
            'filter', 'washer', 'retainer', 'belt', 'spring', 'gear', 'cog',
            'bearing', 'seal', 'gasket', 'pump', 'sensor', 'actuator', 'module',
            'chain', 'pulley', 'rotor', 'caliper', 'brake pad', 'oil filter',
            'air filter', 'spark plug', 'injector', 'valve', 'cylinder', 'housing',
            'engine', 'transmission', 'brake', 'suspension', 'steering', 'exhaust',
            'radiator', 'alternator', 'battery', 'starter', 'clutch', 'differential',
            'carburetor', 'throttle body', 'intake manifold', 'exhaust manifold'
        ])