"""DeepSeek API client."""
import json
from typing import Optional
import httpx
from app.config import settings
from app.models.schemas import GPTAnalysisResponse, NutritionTotals


class DeepSeekClient:
    """Client for DeepSeek API."""
    
    def __init__(self):
        """Initialize DeepSeek client."""
        self.api_key = settings.deepseek_api_key
        self.base_url = "https://api.deepseek.com/v1"
    
    def analyze_food_query(self, prompt: str) -> Optional[GPTAnalysisResponse]:
        """
        Analyze food query using DeepSeek.
        
        Args:
            prompt: The formatted prompt to send to DeepSeek
            
        Returns:
            Parsed response or None if API fails
        """
        if not self.api_key:
            return None
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "system", "content": "You are a food analysis assistant. Return only valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 1000
                    }
                )
                
                if response.status_code != 200:
                    print(f"DeepSeek API error: {response.status_code}")
                    return None
                
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()
                
                # Remove markdown code blocks if present
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                # Parse JSON
                parsed_data = json.loads(content)
                return GPTAnalysisResponse(**parsed_data)
                
        except Exception as e:
            print(f"DeepSeek API error: {e}")
            return None
    
    def estimate_calories(self, prompt: str) -> Optional[NutritionTotals]:
        """
        Estimate calories using DeepSeek (for comparison purposes).
        
        Args:
            prompt: The formatted prompt asking for calorie estimation
            
        Returns:
            Nutrition totals or None if API fails
        """
        if not self.api_key:
            return None
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "system", "content": "You are a nutritionist. Return only valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 200
                    }
                )
                
                if response.status_code != 200:
                    print(f"DeepSeek calorie estimation error: {response.status_code}")
                    return None
                
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()
                
                # Remove markdown code blocks if present
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                # Parse JSON
                parsed_data = json.loads(content)
                return NutritionTotals(**parsed_data)
                
        except Exception as e:
            print(f"DeepSeek calorie estimation error: {e}")
            return None


# Global instance
deepseek_client = DeepSeekClient()
