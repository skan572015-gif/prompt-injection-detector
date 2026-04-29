"""
LLM handler for communicating with Ollama models.
"""

import json
import requests
from typing import Optional, Sequence
from config import OLLAMA_BASE_URL, DEFAULT_MODEL, SYSTEM_PROMPT


class OllamaConnectionError(Exception):
    """Raised when unable to connect to Ollama."""
    pass


class InvalidModelError(Exception):
    """Raised when the specified model is not available."""
    pass


class InvalidLLMResponseError(Exception):
    """Raised when the LLM response is not valid JSON."""
    pass


def check_ollama_connection(base_url: str = OLLAMA_BASE_URL) -> bool:
    """
    Check if Ollama is running and accessible.
    
    Args:
        base_url: The base URL of the Ollama instance.
        
    Returns:
        True if connection is successful, False otherwise.
    """
    # Try a couple of common health endpoints for different Ollama versions
    endpoints = ["/api/tags", "/api/models", "/api/ping"]
    for ep in endpoints:
        try:
            response = requests.get(f"{base_url}{ep}", timeout=5)
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            continue
    return False


def check_model_available(
    model: str = DEFAULT_MODEL,
    base_url: str = OLLAMA_BASE_URL
) -> bool:
    """
    Check if a specific model is available in Ollama.
    
    Args:
        model: The model name to check.
        base_url: The base URL of the Ollama instance.
        
    Returns:
        True if model is available, False otherwise.
    """
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        if response.status_code != 200:
            response = requests.get(f"{base_url}/api/models", timeout=5)

        if response.status_code == 200:
            data = response.json()

            # Normalize different possible response shapes
            models_list = []
            if isinstance(data, dict):
                # common key names: models, tags
                candidates = data.get("models") or data.get("tags") or []
                if isinstance(candidates, list):
                    for m in candidates:
                        if isinstance(m, dict):
                            name = m.get("name", "")
                        else:
                            name = str(m)
                        if name:
                            models_list.append(name)
            elif isinstance(data, list):
                for m in data:
                    if isinstance(m, dict):
                        name = m.get("name", "")
                    else:
                        name = str(m)
                    if name:
                        models_list.append(name)

            # Support both exact tagged names (e.g. qwen3:8b)
            # and base names (e.g. llama3) for backwards compatibility.
            normalized_names = set(models_list)
            normalized_names.update(name.split(":")[0] for name in models_list)

            return model in normalized_names
    except requests.exceptions.RequestException:
        pass
    return False


def query_llm(
    user_input: str,
    prefilter_hints: Optional[Sequence[str]] = None,
    model: str = DEFAULT_MODEL,
    base_url: str = OLLAMA_BASE_URL
) -> str:
    """
    Send a request to the Ollama LLM for classification.
    
    Args:
        user_input: The user prompt to classify.
        prefilter_hints: Regex-based hint categories from the pre-filter stage.
        model: The model to use (default: qwen3:8b).
        base_url: The base URL of the Ollama instance.
        
    Returns:
        The LLM's response as a string.
        
    Raises:
        OllamaConnectionError: If unable to connect to Ollama.
        InvalidModelError: If the specified model is not available.
        InvalidLLMResponseError: If the response is not valid JSON.
    """
    
    # Check connection with better error messages
    if not check_ollama_connection(base_url):
        # Try to provide helpful debugging info
        error_msg = f"Unable to connect to Ollama at {base_url}.\n\n"
        error_msg += "TROUBLESHOOTING STEPS:\n"
        error_msg += "1. Make sure Ollama is running:\n"
        error_msg += "   Open a terminal and run: ollama serve\n"
        error_msg += "2. Check that Ollama is listening on the correct port:\n"
        error_msg += "   Run: netstat -ano | findstr :11434\n"
        error_msg += "3. If the port is blocked, try restarting Ollama:\n"
        error_msg += "   taskkill /F /IM ollama.exe (on Windows)\n"
        error_msg += f"4. Verify {model} is installed:\n"
        error_msg += "   ollama list"
        raise OllamaConnectionError(error_msg)
    
    # Check model availability
    if not check_model_available(model, base_url):
        raise InvalidModelError(
            f"Model '{model}' is not available in Ollama. "
            f"Pull it with: ollama pull {model}"
        )
    
    hint_list = list(prefilter_hints or [])
    hint_text = ", ".join(hint_list) if hint_list else "none"

    # Build the request payload
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": (
                    "Classify this prompt using semantic meaning ONLY.\n"
                    f"Pre-filter regex hint categories: {hint_text}\n"
                    "IMPORTANT: Pre-filter regex matches are only hints. Do NOT use them as the final label. The final attack_type must be based ONLY on semantic meaning and priority rules.\n"
                    "Priority reminders:\n"
                    "- Prefer payload_splitting over instruction_override when the malicious instruction uses variables, concatenation, decoding, reconstruction, or staged first-then / step-by-step structure.\n"
                    "- Prefer indirect_injection over instruction_override when malicious instructions are embedded inside another task such as summarize, translate, analyze, process, or read.\n\n"
                    f"Prompt to classify:\n{user_input}"
                )
            }
        ],
        "stream": False,
        # Qwen3 models may emit reasoning in a separate `thinking` field and
        # leave `content` empty unless thinking is explicitly disabled.
        "think": False,
        "options": {
            "temperature": 0,
            "num_predict": 120,
            "num_ctx": 2048
        }
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/chat",
            json=payload,
            timeout=120
        )
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise OllamaConnectionError(
            "Request to Ollama timed out. The LLM took too long to respond."
        )
    except requests.exceptions.RequestException as e:
        raise OllamaConnectionError(
            f"Error communicating with Ollama: {str(e)}"
        )
    
    # Extract the response content
    try:
        response_data = response.json()
        message = response_data.get("message", {})
        llm_response = message.get("content", "")
        thinking_response = message.get("thinking", "")

        if isinstance(llm_response, str):
            llm_response = llm_response.strip()
        else:
            llm_response = str(llm_response).strip()

        if isinstance(thinking_response, str):
            thinking_response = thinking_response.strip()
        else:
            thinking_response = str(thinking_response).strip()
        
        if not llm_response:
            if thinking_response:
                raise InvalidLLMResponseError(
                    "Ollama returned reasoning in `message.thinking` but no final "
                    "answer in `message.content`. Thinking must be disabled for this model."
                )
            raise InvalidLLMResponseError(
                "Ollama returned an empty response."
            )
        
        return llm_response
        
    except (json.JSONDecodeError, KeyError) as e:
        raise InvalidLLMResponseError(
            f"Failed to parse Ollama response: {str(e)}"
        )


def extract_json_from_response(response_text: str) -> dict:
    """
    Extract and parse JSON from LLM response.
    
    Handles cases where the LLM might wrap JSON in markdown blocks or refuse.
    If no valid JSON is found, returns a fallback classification result.
    
    Args:
        response_text: The raw response from the LLM.
        
    Returns:
        Parsed JSON as a dictionary, or fallback JSON if extraction fails.
    """
    import re
    
    # Fallback result for when LLM refuses or returns invalid response
    fallback_result = {
        "is_malicious": True,
        "attack_type": "direct_injection",
        "risk": "high",
        "explanation": "The LLM did not return valid JSON. The input was treated as suspicious by default."
    }
    
    if not response_text or not response_text.strip():
        return fallback_result
    
    # Try parsing directly first
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    
    # Try removing markdown code block markers (```json ... ```)
    if "```json" in response_text:
        start = response_text.find("```json") + len("```json")
        end = response_text.find("```", start)
        if end != -1:
            json_str = response_text[start:end].strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
    
    # Try removing any ``` markers (``` ... ```)
    if "```" in response_text:
        start = response_text.find("```") + 3
        end = response_text.find("```", start)
        if end != -1:
            json_str = response_text[start:end].strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
    
    # Use regex to find JSON object pattern { ... }
    # This handles cases where JSON is embedded in text
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_pattern, response_text)
    
    if matches:
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
    
    # Last resort: find { and } and try to parse
    start = response_text.find("{")
    end = response_text.rfind("}") + 1
    if start != -1 and end > start:
        json_str = response_text[start:end]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    # If all extraction attempts fail, return fallback result
    return fallback_result
