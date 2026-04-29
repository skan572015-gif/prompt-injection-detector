"""
Main entry point for the Prompt Injection Detection system.
"""

import sys
from typing import Optional
from classifier import classify_prompt, ClassificationError


def print_header():
    """Print the application header."""
    print("\n" + "=" * 70)
    print("LLM-BASED PROMPT INJECTION DETECTION AND SAFEGUARDING SYSTEM")
    print("=" * 70)
    print()


def get_attack_description(attack_type: str) -> str:
    """
    Get a brief description of each attack type.
    
    Args:
        attack_type: The attack type string.
        
    Returns:
        Description of the attack type.
    """
    descriptions = {
        "system_prompt_exfiltration": "Attempt to extract hidden system instructions",
        "payload_splitting": "Malicious intent hidden across multiple parts",
        "indirect_injection": "Harmful instructions hidden in external content",
        "persona_jailbreak": "Attempt to bypass safety by assigning a role",
        "instruction_override": "Explicit directive to ignore existing rules",
        "direct_injection": "Direct command to perform prohibited actions",
        "none": "Benign input with no malicious intent"
    }
    return descriptions.get(attack_type, "Unknown attack type")


def get_risk_icon(risk: str) -> str:
    """
    Get an icon for risk level.
    
    Args:
        risk: The risk level (low, medium, high).
        
    Returns:
        Icon representation of risk level.
    """
    risk_icons = {
        "low": "🟢",
        "medium": "🟡",
        "high": "🔴"
    }
    return risk_icons.get(risk, "❓")


def print_results(classification_result, pre_filter_result):
    """
    Print the classification results in a readable format.
    
    Args:
        classification_result: The ClassificationResult from the LLM.
        pre_filter_result: The PreFilterResult from the filter.
    """
    
    # Determine status and color
    if classification_result.is_malicious:
        status = "🚨 MALICIOUS"
    else:
        status = "✅ SAFE"
    
    print("\n" + "-" * 70)
    print(f"FINAL DECISION: {status}")
    print("-" * 70)
    
    if classification_result.is_malicious:
        attack_type = classification_result.attack_type
        risk = classification_result.risk
        risk_icon = get_risk_icon(risk)
        description = get_attack_description(attack_type)
        
        print(f"Attack Type:    {attack_type.upper().replace('_', ' ')}")
        print(f"Description:    {description}")
        print(f"Risk Level:     {risk_icon} {risk.upper()}")
    else:
        print(f"Classification: ✅ Benign prompt (no attack detected)")
    
    print(f"Explanation:    {classification_result.explanation}")
    
    # Show pre-filter information if suspicious patterns were found
    if pre_filter_result.is_suspicious:
        print("\n📌 Pre-filter Alert (patterns detected):")
        print(f"   Matched: {', '.join(pre_filter_result.matched_patterns)}")
        print("   (LLM made the final classification decision)")
    
    print("-" * 70 + "\n")


def print_error(error_message: str):
    """
    Print an error message.
    
    Args:
        error_message: The error message to display.
    """
    print("\n" + "!" * 70)
    print("ERROR")
    print("!" * 70)
    print(f"{error_message}")
    print("!" * 70 + "\n")


def get_user_input() -> Optional[str]:
    """
    Get input from the user.
    
    Returns:
        The user's prompt, or None if they want to exit.
    """
    print("\nEnter a prompt to analyze (or 'quit' to exit):")
    user_input = input("> ").strip()
    
    if user_input.lower() in ["quit", "exit", "q"]:
        return None
    
    return user_input


def main():
    """Main application loop."""
    print_header()
    
    print("This system detects 7 prompt categories:")
    print()
    print("  1. SYSTEM_PROMPT_EXFILTRATION - Extract hidden instructions")
    print("  2. PAYLOAD_SPLITTING - Obfuscate intent across parts")
    print("  3. INDIRECT_INJECTION - Hide malice in external content")
    print("  4. PERSONA_JAILBREAK - Assign unrestricted role/persona")
    print("  5. INSTRUCTION_OVERRIDE - Force ignore of rules")
    print("  6. DIRECT_INJECTION - Direct command override")
    print("  7. NONE - Benign, safe input")
    print()
    print("Risk Levels: 🟢 LOW | 🟡 MEDIUM | 🔴 HIGH")
    print()
    print("⚠️  IMPORTANT: Ensure Ollama is running:")
    print("   Open another terminal and run: ollama serve")
    print()
    
    while True:
        try:
            user_input = get_user_input()
            
            if user_input is None:
                print("Exiting...")
                break
            
            if not user_input:
                print("Please enter a non-empty prompt.")
                continue
            
            print(f"\nAnalyzing: \"{user_input}\"")
            print("Calling LLM for semantic analysis...")
            
            # Perform classification
            classification_result, pre_filter_result = classify_prompt(user_input)
            
            # Print results
            print_results(classification_result, pre_filter_result)
            
        except ClassificationError as e:
            print_error(str(e))
        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Exiting...")
            break
        except Exception as e:
            print_error(f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()
