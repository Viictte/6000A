"""
Utility Helper Functions
"""

import re
from datetime import datetime

def validate_topic(topic):
    """
    Validate if topic is legitimate
    
    Args:
        topic: User input topic
        
    Returns:
        bool: Whether valid
    """
    if not topic or not topic.strip():
        return False
    
    # Length limit
    if len(topic) > 100:
        return False
    
    # Check for forbidden characters
    forbidden_patterns = [
        r'<script',
        r'javascript:',
        r'onerror=',
        r'onclick='
    ]
    
    topic_lower = topic.lower()
    for pattern in forbidden_patterns:
        if re.search(pattern, topic_lower):
            return False
    
    return True


def sanitize_input(text):
    """
    Clean user input to prevent XSS and SQL injection
    
    Args:
        text: User input text
        
    Returns:
        str: Sanitized text
    """
    if not text:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove special characters
    text = text.replace('<', '').replace('>', '')
    text = text.replace('"', '').replace("'", '')
    
    # Limit length
    text = text[:200]
    
    return text.strip()


def format_age_group(age_group):
    """
    Format age group
    
    Args:
        age_group: Age group string
        
    Returns:
        str: Formatted age group
    """
    valid_age_groups = ['3-5', '6-8', '9-12']
    
    if age_group in valid_age_groups:
        return age_group
    
    # Default return 6-8 years
    return '6-8'


def get_timestamp():
    """
    Get current timestamp
    
    Returns:
        str: Formatted timestamp
    """
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def is_safe_content(text):
    """
    Check if content is safe (child-friendly)
    
    Args:
        text: Text to check
        
    Returns:
        bool: Whether safe
    """
    # Unsafe keywords list
    unsafe_keywords = [
        'violence', 'blood', 'terror', 'porn',
        'gambling', 'drugs', 'weapon', 'danger'
    ]
    
    text_lower = text.lower()
    
    for keyword in unsafe_keywords:
        if keyword in text_lower:
            return False
    
    return True


def truncate_text(text, max_length=50):
    """
    Truncate text to specified length
    
    Args:
        text: Original text
        max_length: Maximum length
        
    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length] + '...'


def extract_emojis(text):
    """
    Extract emojis from text
    
    Args:
        text: Text
        
    Returns:
        list: List of emojis
    """
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    
    return emoji_pattern.findall(text)