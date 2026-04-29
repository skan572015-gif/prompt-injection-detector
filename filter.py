"""
Lightweight pre-filtering module using keyword and regex patterns.
Detects obvious suspicious patterns before LLM analysis.
"""

import re
from models import PreFilterResult
from config import SUSPICIOUS_PATTERNS


def perform_pre_filtering(user_input: str) -> PreFilterResult:
    """
    Perform lightweight keyword and regex-based filtering on user input.
    
    This is a fast first-pass filter that catches obvious suspicious patterns.
    It does NOT replace LLM-based classification but acts as a supplementary signal.
    
    Args:
        user_input: The user prompt to filter.
        
    Returns:
        PreFilterResult with is_suspicious flag and matched pattern categories.
    """
    if not user_input or not user_input.strip():
        return PreFilterResult(is_suspicious=False, matched_patterns=[])
    
    # Normalize input for pattern matching
    normalized_input = user_input.lower().strip()
    
    matched_patterns = []
    
    # Check each pattern category
    for category, patterns in SUSPICIOUS_PATTERNS.items():
        for pattern in patterns:
            try:
                if re.search(pattern, normalized_input, re.IGNORECASE):
                    matched_patterns.append(category)
                    break  # Move to next category once matched
            except re.error:
                # Skip malformed regex patterns
                continue
    
    is_suspicious = len(matched_patterns) > 0
    
    return PreFilterResult(
        is_suspicious=is_suspicious,
        matched_patterns=matched_patterns
    )
