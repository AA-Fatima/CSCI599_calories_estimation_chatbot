"""OpenAI GPT client."""
import json
from typing import Optional
from openai import OpenAI
from app.config import settings
from app.models.schemas import GPTAnalysisResponse, NutritionTotals


class GPTClient:
    """Client for OpenAI GPT API."""
    
    def __init__(self):
        """Initialize GPT client."""
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
    
    def analyze_food_query(self, prompt: str) -> Optional[GPTAnalysisResponse]:
        """
        Analyze food query using GPT.
        
        Args:
            prompt: The formatted prompt to send to GPT
            
        Returns:
            Parsed GPT response or None if API fails
        """
        if not self.client:
            return None
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a food analysis assistant. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            # Parse JSON
            data = json.loads(content)
            return GPTAnalysisResponse(**data)
            
        except Exception as e:
            print(f"GPT API error: {e}")
            return None
    
    def estimate_calories(self, prompt: str) -> Optional[NutritionTotals]:
        """
        Estimate calories using GPT (for comparison purposes).
        
        Args:
            prompt: The formatted prompt asking for calorie estimation
            
        Returns:
            Nutrition totals or None if API fails
        """
        if not self.client:
            return None
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a nutritionist. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            # Parse JSON
            data = json.loads(content)
            return NutritionTotals(**data)
            
        except Exception as e:
            print(f"GPT calorie estimation error: {e}")
            return None


# Global instance
gpt_client = GPTClient()
