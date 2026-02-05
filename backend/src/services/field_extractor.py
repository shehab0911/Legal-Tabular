"""
Field extraction service using AI/LLM with citations and confidence scoring.
"""

import json
import re
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class FieldExtractor:
    """Extracts fields from documents with citations and confidence scoring."""

    def __init__(self, llm_client=None):
        """
        Initialize extractor.
        
        Args:
            llm_client: Optional LLM client for extraction (ChatGPT, Claude, etc.)
        """
        self.llm_client = llm_client

    def extract_fields(
        self,
        document_text: str,
        document_chunks: List[Dict[str, Any]],
        field_definitions: List[Dict[str, Any]],
        document_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Extract fields from document with citations and confidence.
        
        Args:
            document_text: Full document text
            document_chunks: List of chunks with metadata
            field_definitions: List of fields to extract
            document_id: Document identifier
            
        Returns:
            List of extraction results with citations and confidence
        """
        results = []
        
        for field_def in field_definitions:
            field_name = field_def.get('name', '')
            field_type = field_def.get('field_type', 'TEXT')
            description = field_def.get('description', '')
            
            extraction = self._extract_single_field(
                document_text=document_text,
                document_chunks=document_chunks,
                field_name=field_name,
                field_type=field_type,
                description=description,
                document_id=document_id,
            )
            
            results.append(extraction)
        
        return results

    def _extract_single_field(
        self,
        document_text: str,
        document_chunks: List[Dict[str, Any]],
        field_name: str,
        field_type: str,
        description: str,
        document_id: str,
    ) -> Dict[str, Any]:
        """Extract a single field with citations and confidence."""
        
        try:
            # Use LLM if available, otherwise use heuristics
            if self.llm_client:
                extraction_result = self._extract_with_llm(
                    document_text, field_name, field_type, description
                )
            else:
                extraction_result = self._extract_with_heuristics(
                    document_text, document_chunks, field_name, field_type
                )
            
            extracted_value = extraction_result.get('value')
            raw_text = extraction_result.get('raw_text')
            confidence = extraction_result.get('confidence', 0.0)
            
            # Find and rank citations
            citations = self._find_citations(
                raw_text or extracted_value,
                document_chunks,
                document_id,
                top_k=3
            )
            
            # Normalize value
            normalized_value = self._normalize_value(extracted_value, field_type)
            
            # Validate and adjust confidence
            validation_score = self._validate_extraction(
                extracted_value, normalized_value, field_type
            )
            final_confidence = min(1.0, confidence * validation_score)
            
            return {
                'field_name': field_name,
                'field_type': field_type,
                'extracted_value': extracted_value,
                'raw_text': raw_text,
                'normalized_value': normalized_value,
                'confidence_score': final_confidence,
                'citations': citations,
                'extraction_metadata': {
                    'method': 'llm' if self.llm_client else 'heuristic',
                    'extracted_at': datetime.utcnow().isoformat(),
                }
            }
        except Exception as e:
            logger.error(f"Error extracting field {field_name}: {str(e)}")
            return {
                'field_name': field_name,
                'field_type': field_type,
                'extracted_value': None,
                'raw_text': None,
                'normalized_value': None,
                'confidence_score': 0.0,
                'citations': [],
                'error': str(e),
            }

    def _extract_with_llm(
        self,
        document_text: str,
        field_name: str,
        field_type: str,
        description: str,
    ) -> Dict[str, Any]:
        """Extract field using LLM."""
        prompt = f"""
Extract the following field from the legal document:

Field Name: {field_name}
Field Type: {field_type}
Description: {description}

Document:
{document_text[:5000]}...

Please provide:
1. The extracted value
2. The raw text from the document supporting this extraction
3. Your confidence score (0.0-1.0)

Respond in JSON format:
{{
    "value": "...",
    "raw_text": "...",
    "confidence": 0.0
}}
"""
        try:
            response = self.llm_client.complete(prompt)
            result = json.loads(response)
            return {
                'value': result.get('value'),
                'raw_text': result.get('raw_text'),
                'confidence': min(1.0, result.get('confidence', 0.0)),
            }
        except Exception as e:
            logger.error(f"LLM extraction error: {str(e)}")
            return {'value': None, 'raw_text': None, 'confidence': 0.0}

    def _extract_with_heuristics(
        self,
        document_text: str,
        document_chunks: List[Dict[str, Any]],
        field_name: str,
        field_type: str,
    ) -> Dict[str, Any]:
        """Extract field using heuristic patterns."""
        
        patterns = self._get_patterns_for_field(field_name, field_type)
        
        for pattern, confidence_boost in patterns:
            matches = re.finditer(pattern, document_text, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                extracted_value = match.group(1) if match.groups() else match.group(0)
                
                # Get context around match
                start = max(0, match.start() - 100)
                end = min(len(document_text), match.end() + 100)
                context = document_text[start:end]
                
                confidence = min(1.0, 0.6 + confidence_boost)
                
                return {
                    'value': extracted_value.strip(),
                    'raw_text': context.strip(),
                    'confidence': confidence,
                }
        
        # No match found
        return {'value': None, 'raw_text': None, 'confidence': 0.0}

    @staticmethod
    def _get_patterns_for_field(field_name: str, field_type: str) -> List[Tuple[str, float]]:
        """Get regex patterns for common legal fields."""
        patterns = []
        
        field_name_lower = field_name.lower()
        
        # Common field patterns
        if 'date' in field_name_lower or field_type == 'DATE':
            patterns = [
                (r'(\d{1,2}/\d{1,2}/\d{4})', 0.3),
                (r'(\d{4}-\d{2}-\d{2})', 0.3),
                (r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}', 0.4),
            ]
        elif 'party' in field_name_lower or 'parties' in field_name_lower:
            patterns = [
                (r'(?:Between|BETWEEN|between)\s+([A-Z][A-Za-z\s&.,]+?)\s+(?:and|AND)', 0.3),
                (r'(?:Party|PARTY):\s*([A-Z][A-Za-z\s&.,]+?)(?:\n|;)', 0.4),
            ]
        elif 'effective' in field_name_lower or 'term' in field_name_lower:
            patterns = [
                (r'(?:effective|Effective|EFFECTIVE)(?:\s+date)?[:\s]+([A-Za-z0-9\s,./\-]+?)(?:[,;]|and|on)', 0.3),
                (r'(?:term|Term|TERM)[:\s]+([A-Za-z0-9\s,./\-]+?)(?:[,;]|and|\n)', 0.3),
            ]
        elif 'currency' in field_name_lower or 'amount' in field_name_lower or field_type == 'CURRENCY':
            patterns = [
                (r'\$[\d,]+\.?\d*', 0.4),
                (r'(USD|EUR|GBP)[\s]*[\d,]+\.?\d*', 0.3),
            ]
        elif 'liable' in field_name_lower or 'liability' in field_name_lower:
            patterns = [
                (r'(?:liability|Liability|LIABLE)[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|and|as)', 0.3),
            ]
        
        # Generic pattern for any field
        patterns.append((r'(?:' + re.escape(field_name) + r')[:\s]+([A-Za-z0-9\s,\-$().%]+?)(?:[.;]|and)', 0.2))
        
        return patterns

    def _find_citations(
        self,
        query_text: str,
        document_chunks: List[Dict[str, Any]],
        document_id: str,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """Find relevant citations in document chunks."""
        citations = []
        
        if not query_text:
            return citations
        
        # Score chunks by similarity to query
        scored_chunks = []
        query_tokens = set(query_text.lower().split())
        
        for i, chunk in enumerate(document_chunks):
            chunk_text = chunk.get('text', '')
            chunk_tokens = set(chunk_text.lower().split())
            
            # Calculate Jaccard similarity
            intersection = len(query_tokens & chunk_tokens)
            union = len(query_tokens | chunk_tokens)
            similarity = intersection / union if union > 0 else 0.0
            
            # Boost score if query text is directly in chunk
            if query_text.lower() in chunk_text.lower():
                similarity = min(1.0, similarity + 0.3)
            
            scored_chunks.append({
                'text': chunk_text,
                'similarity': similarity,
                'page': chunk.get('page_number', 1),
                'section': chunk.get('section', 'Main'),
                'chunk_id': str(i),
            })
        
        # Sort and get top-k
        scored_chunks.sort(key=lambda x: x['similarity'], reverse=True)
        
        for i, chunk in enumerate(scored_chunks[:top_k]):
            if chunk['similarity'] > 0.0:
                citations.append({
                    'citation_text': chunk['text'][:500],
                    'page_number': chunk['page'],
                    'section_title': chunk['section'],
                    'relevance_score': chunk['similarity'],
                    'chunk_id': chunk['chunk_id'],
                })
        
        return citations

    @staticmethod
    def _normalize_value(value: Optional[str], field_type: str) -> Optional[str]:
        """Normalize extracted value based on field type."""
        if not value:
            return None
        
        value = value.strip()
        
        if field_type == 'DATE':
            # Try to normalize to YYYY-MM-DD format
            date_patterns = [
                (r'(\d{1,2})/(\d{1,2})/(\d{4})', lambda m: f"{m.group(3)}-{m.group(1):0>2}-{m.group(2):0>2}'),
                (r'(\d{4})-(\d{2})-(\d{2})', lambda m: m.group(0)),
            ]
            for pattern, normalizer in date_patterns:
                match = re.search(pattern, value)
                if match:
                    return normalizer(match)
        
        elif field_type == 'CURRENCY':
            # Extract numeric value
            match = re.search(r'\$?([\d,]+\.?\d*)', value)
            if match:
                num_str = match.group(1).replace(',', '')
                return f"USD {num_str}"
        
        elif field_type == 'BOOLEAN':
            value_lower = value.lower()
            if any(word in value_lower for word in ['yes', 'true', 'agreed', 'confirmed']):
                return 'true'
            elif any(word in value_lower for word in ['no', 'false', 'denied', 'rejected']):
                return 'false'
        
        elif field_type == 'ENTITY':
            # Capitalize properly
            return ' '.join(word.capitalize() for word in value.split())
        
        return value

    @staticmethod
    def _validate_extraction(
        extracted_value: Optional[str],
        normalized_value: Optional[str],
        field_type: str,
    ) -> float:
        """Validate extraction and return confidence adjustment."""
        if not extracted_value:
            return 0.0
        
        # Check if normalization was successful
        if not normalized_value:
            return 0.5
        
        # Type-specific validation
        if field_type == 'DATE':
            if re.match(r'\d{4}-\d{2}-\d{2}', normalized_value):
                return 1.0
            return 0.6
        
        elif field_type == 'CURRENCY':
            if 'USD' in normalized_value and re.search(r'[\d,]+\.?\d*', normalized_value):
                return 1.0
            return 0.6
        
        elif field_type == 'BOOLEAN':
            if normalized_value in ['true', 'false']:
                return 1.0
            return 0.5
        
        # Generic validation
        return 0.8
