import re
from typing import Any

def validate_input(message: str) -> bool:
    """Validate user input"""
    if not message or not isinstance(message, str):
        return False
    
    # Check length
    if len(message.strip()) < 2 or len(message) > 500:
        return False
    
    # Check for potentially harmful content
    harmful_patterns = [
        r'<script',
        r'javascript:',
        r'eval\(',
        r'exec\('
    ]
    
    msg_lower = message.lower()
    if any(re.search(pattern, msg_lower) for pattern in harmful_patterns):
        return False
    
    return True

def format_response(response: Any) -> str:
    """Format response for chat display"""
    if isinstance(response, dict):
        return str(response)
    elif isinstance(response, str):
        # Ensure response isn't too long for chat
        if len(response) > 1000:
            return response[:950] + "... (truncated)"
        return response
    else:
        return str(response)

def extract_numbers(text: str) -> list:
    """Extract numbers from text"""
    return [int(x) for x in re.findall(r'\d+', text)]

def clean_text(text: str) -> str:
    """Clean and normalize text"""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove special characters except basic punctuation
    text = re.sub(r'[^\w\s.,!?-]', '', text)
    
    return text