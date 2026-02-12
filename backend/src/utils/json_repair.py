"""
JSON Repair Utility - Attempts to fix common JSON formatting issues
"""
import json
import re
from typing import Dict, Any, Optional


def repair_json(json_str: str) -> Optional[str]:
    """
    Attempt to repair common JSON formatting issues
    
    Args:
        json_str: Potentially malformed JSON string
        
    Returns:
        Repaired JSON string or None if repair failed
    """
    try:
        # Already valid JSON
        json.loads(json_str)
        return json_str
    except json.JSONDecodeError:
        pass
    
    # Try various repair strategies
    repaired = json_str
    
    # 1. Fix trailing commas in arrays and objects
    repaired = re.sub(r',\s*]', ']', repaired)
    repaired = re.sub(r',\s*}', '}', repaired)
    
    # 2. Fix missing commas between array string elements (more aggressive)
    # Match: "string"\n  "string" and add comma
    repaired = re.sub(r'"\s*\n\s+"', '",\n"', repaired)
    
    # 3. Fix missing commas between object properties
    # Match: "key": value\n  "nextkey": and add comma after value
    repaired = re.sub(r'(:\s*"[^"]*")\s*\n\s*"', r'\1,\n"', repaired)
    repaired = re.sub(r'(:\s*\d+)\s*\n\s*"', r'\1,\n"', repaired)
    repaired = re.sub(r'(:\s*true|false|null)\s*\n\s*"', r'\1,\n"', repaired)
    
    # 4. Fix missing commas after closing brackets/braces
    repaired = re.sub(r']\s*\n\s*"', '],\n"', repaired)
    repaired = re.sub(r'}\s*\n\s*"', '},\n"', repaired)
    
    # 5. Ensure proper closing brackets
    open_braces = repaired.count('{')
    close_braces = repaired.count('}')
    if open_braces > close_braces:
        repaired += '}' * (open_braces - close_braces)
    
    open_brackets = repaired.count('[')
    close_brackets = repaired.count(']')
    if open_brackets > close_brackets:
        repaired += ']' * (open_brackets - close_brackets)
    
    # 6. Remove any trailing text after final closing brace
    last_brace = repaired.rfind('}')
    if last_brace != -1:
        repaired = repaired[:last_brace + 1]
    
    # Test if repair worked
    try:
        json.loads(repaired)
        return repaired
    except json.JSONDecodeError:
        return None


def parse_json_with_repair(json_str: str, max_attempts: int = 3) -> Optional[Dict[str, Any]]:
    """
    Parse JSON with automatic repair attempts
    
    Args:
        json_str: JSON string to parse
        max_attempts: Maximum number of repair attempts
        
    Returns:
        Parsed JSON dict or None if all attempts failed
    """
    # First attempt: parse as-is
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Initial JSON parse failed: {e}")
    
    # Second attempt: try repair
    print("Attempting JSON repair...")
    repaired = repair_json(json_str)
    if repaired:
        try:
            result = json.loads(repaired)
            print("✓ JSON repair successful!")
            return result
        except json.JSONDecodeError as e:
            print(f"Repaired JSON still invalid: {e}")
    
    # Third attempt: try more aggressive repair
    print("Attempting aggressive JSON repair...")
    
    # Extract just the main object
    start = json_str.find('{')
    end = json_str.rfind('}')
    if start != -1 and end != -1:
        extracted = json_str[start:end + 1]
        repaired = repair_json(extracted)
        if repaired:
            try:
                result = json.loads(repaired)
                print("✓ Aggressive JSON repair successful!")
                return result
            except json.JSONDecodeError:
                pass
    
    print("✗ All JSON repair attempts failed")
    return None


if __name__ == "__main__":
    # Test cases
    test_cases = [
        # Trailing comma
        '{"name": "John", "age": 30,}',
        # Missing comma
        '{"name": "John" "age": 30}',
        # Unclosed brace
        '{"name": "John", "age": 30',
        # Valid JSON (should pass through)
        '{"name": "John", "age": 30}',
    ]
    
    for i, test in enumerate(test_cases):
        print(f"\nTest {i + 1}: {test}")
        result = parse_json_with_repair(test)
        print(f"Result: {result}")
