"""
Main classification orchestrator that coordinates all modules.
"""

from models import ClassificationResult, PreFilterResult
from filter import perform_pre_filtering
from llm_handler import (
    query_llm,
    extract_json_from_response,
    OllamaConnectionError,
    InvalidModelError,
    InvalidLLMResponseError,
)
from pydantic import ValidationError


class ClassificationError(Exception):
    """Base exception for classification errors."""
    pass


def classify_prompt(user_input: str) -> tuple[ClassificationResult, PreFilterResult]:
    """
    Classify a user prompt for prompt injection attacks.
    
    This function orchestrates the full classification pipeline:
    1. Pre-filtering (fast keyword matching)
    2. LLM-based semantic analysis
    3. Validation of results
    
    Args:
        user_input: The user prompt to classify.
        
    Returns:
        Tuple of (ClassificationResult, PreFilterResult).
        
    Raises:
        ClassificationError: If classification fails at any stage.
    """
    
    # Validate input
    if not user_input or not user_input.strip():
        raise ClassificationError("Input cannot be empty.")
    
    # Step 1: Pre-filtering
    pre_filter_result = perform_pre_filtering(user_input)
    
    # Step 2: Query LLM
    try:
        llm_response = query_llm(user_input)
    except OllamaConnectionError as e:
        raise ClassificationError(f"Connection error: {str(e)}")
    except InvalidModelError as e:
        raise ClassificationError(f"Model error: {str(e)}")
    except InvalidLLMResponseError as e:
        raise ClassificationError(f"LLM response error: {str(e)}")
    
    # Step 3: Extract JSON (now returns fallback if extraction fails)
    response_json = extract_json_from_response(llm_response)
    
    # Step 4: Validate and parse with Pydantic
    try:
        classification_result = ClassificationResult(**response_json)
    except ValidationError as e:
        raise ClassificationError(
            f"Validation error: {str(e)}. "
            f"Ensure LLM returned valid fields: is_malicious, attack_type, risk, explanation."
        )
    
    return classification_result, pre_filter_result
