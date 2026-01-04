"""Parse AI responses to structured data."""
from typing import Optional
from app.models.schemas import GPTAnalysisResponse


def parse_gpt_response(raw_response: str) -> Optional[GPTAnalysisResponse]:
    """
    Parse raw GPT response to structured data.
    
    This is a fallback parser if the AI client doesn't handle it.
    
    Args:
        raw_response: Raw string response from AI
        
    Returns:
        Parsed GPT response or None
    """
    try:
        import json
        
        # Clean up the response
        response = raw_response.strip()
        
        # Remove markdown code blocks
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        # Parse JSON
        data = json.loads(response)
        return GPTAnalysisResponse(**data)
        
    except Exception as e:
        print(f"Error parsing GPT response: {e}")
        return None
