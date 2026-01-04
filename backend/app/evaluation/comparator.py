"""Comparator - runs comparison tests."""
import pandas as pd
from typing import List
from app.config import settings
from app.models.schemas import (
    TestQuery,
    ComparisonResult,
    NutritionTotals,
    ChatRequest
)
from app.services.chat_service import chat_service
from app.ai.gpt_client import gpt_client
from app.ai.deepseek_client import deepseek_client
from app.ai.prompts import build_calorie_estimation_prompt


class Comparator:
    """Run comparison tests against ChatGPT and DeepSeek."""
    
    def load_test_queries(self) -> List[TestQuery]:
        """Load test queries from Excel file."""
        try:
            df = pd.read_excel(settings.test_queries_path)
            queries = []
            
            for _, row in df.iterrows():
                queries.append(TestQuery(
                    query=row['query'],
                    country=row['country'],
                    expected_calories=row['expected_calories'],
                    expected_carbs=row.get('expected_carbs', 0),
                    expected_protein=row.get('expected_protein', 0),
                    expected_fat=row.get('expected_fat', 0)
                ))
            
            return queries
        except Exception as e:
            print(f"Error loading test queries: {e}")
            return []
    
    def run_comparison(self, queries: List[TestQuery]) -> List[ComparisonResult]:
        """
        Run comparison for all test queries.
        
        Args:
            queries: List of test queries
            
        Returns:
            List of comparison results
        """
        results = []
        
        for query in queries:
            print(f"Processing query: {query.query}")
            
            # Get expected values
            expected = NutritionTotals(
                calories=query.expected_calories,
                carbs=query.expected_carbs or 0,
                protein=query.expected_protein or 0,
                fat=query.expected_fat or 0
            )
            
            # Get chatbot response
            chatbot_result = self._get_chatbot_response(query)
            
            # Get GPT direct estimate
            gpt_result = self._get_gpt_estimate(query)
            
            # Get DeepSeek direct estimate
            deepseek_result = self._get_deepseek_estimate(query)
            
            results.append(ComparisonResult(
                query=query.query,
                expected=expected,
                chatbot=chatbot_result,
                gpt=gpt_result,
                deepseek=deepseek_result
            ))
        
        return results
    
    def _get_chatbot_response(self, query: TestQuery) -> NutritionTotals:
        """Get response from chatbot."""
        try:
            request = ChatRequest(
                message=query.query,
                country=query.country
            )
            response = chat_service.process_message(request)
            return response.totals
        except Exception as e:
            print(f"Chatbot error: {e}")
            return NutritionTotals(calories=0, carbs=0, protein=0, fat=0)
    
    def _get_gpt_estimate(self, query: TestQuery) -> NutritionTotals:
        """Get direct estimate from GPT."""
        try:
            prompt = build_calorie_estimation_prompt(query.query)
            result = gpt_client.estimate_calories(prompt)
            return result if result else NutritionTotals(calories=0, carbs=0, protein=0, fat=0)
        except Exception as e:
            print(f"GPT error: {e}")
            return NutritionTotals(calories=0, carbs=0, protein=0, fat=0)
    
    def _get_deepseek_estimate(self, query: TestQuery) -> NutritionTotals:
        """Get direct estimate from DeepSeek."""
        try:
            prompt = build_calorie_estimation_prompt(query.query)
            result = deepseek_client.estimate_calories(prompt)
            return result if result else NutritionTotals(calories=0, carbs=0, protein=0, fat=0)
        except Exception as e:
            print(f"DeepSeek error: {e}")
            return NutritionTotals(calories=0, carbs=0, protein=0, fat=0)


# Global instance
comparator = Comparator()
