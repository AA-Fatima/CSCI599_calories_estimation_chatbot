"""Comprehensive system evaluation script."""
import asyncio
import sys
import json
from pathlib import Path
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_database
from app.services.chat_service import chat_service
from app.models.schemas import ChatRequest
from app.evaluation.metrics import EvaluationMetrics


async def load_test_dataset(dataset_path: Path) -> List[Dict]:
    """Load evaluation dataset."""
    if not dataset_path.exists():
        logger.error(f"Dataset not found: {dataset_path}")
        return []
    
    with open(dataset_path, 'r', encoding='utf-8') as f:
        return json.load(f)


async def evaluate_query(
    test_case: Dict,
    db: AsyncSession
) -> Dict:
    """Evaluate a single query."""
    request = ChatRequest(
        message=test_case["query"],
        country=test_case.get("country", "lebanon")
    )
    
    try:
        response = await chat_service.process_message(request, db)
        
        return {
            "query": test_case["query"],
            "expected_dish": test_case.get("expected_dish"),
            "predicted_dish": response.dish_name,
            "expected_calories": test_case.get("expected_calories"),
            "predicted_calories": response.totals.calories,
            "match_found": response.dish_name.lower() == test_case.get("expected_dish", "").lower(),
            "source": response.source,
            "success": True
        }
    except Exception as e:
        logger.error(f"Error evaluating query '{test_case['query']}': {e}")
        return {
            "query": test_case["query"],
            "success": False,
            "error": str(e)
        }


async def run_evaluation(dataset_path: Path = None):
    """Run comprehensive system evaluation."""
    if dataset_path is None:
        dataset_path = Path(__file__).parent.parent / "data" / "evaluation" / "test_dataset.json"
    
    logger.info("="*60)
    logger.info("SYSTEM EVALUATION")
    logger.info("="*60)
    
    # Load test dataset
    test_dataset = await load_test_dataset(dataset_path)
    if not test_dataset:
        logger.error("No test dataset available. Please create test_dataset.json")
        return
    
    logger.info(f"Loaded {len(test_dataset)} test cases")
    
    # Evaluate all queries
    results = []
    async for db in get_database():
        for i, test_case in enumerate(test_dataset, 1):
            logger.info(f"[{i}/{len(test_dataset)}] Evaluating: {test_case['query']}")
            result = await evaluate_query(test_case, db)
            results.append(result)
        break
    
    # Calculate metrics
    successful_results = [r for r in results if r.get("success", False)]
    
    if successful_results:
        predictions = [r["predicted_calories"] for r in successful_results]
        ground_truth = [r["expected_calories"] for r in successful_results if r.get("expected_calories")]
        
        if ground_truth and len(predictions) == len(ground_truth):
            metrics = EvaluationMetrics.calculate_accuracy_metrics(predictions, ground_truth)
            
            logger.info("="*60)
            logger.info("EVALUATION RESULTS")
            logger.info("="*60)
            logger.info(f"Total Queries: {len(results)}")
            logger.info(f"Successful: {len(successful_results)}")
            logger.info(f"Failed: {len(results) - len(successful_results)}")
            logger.info("")
            logger.info("Accuracy Metrics:")
            for metric, value in metrics.items():
                logger.info(f"  {metric}: {value:.4f}" if isinstance(value, float) else f"  {metric}: {value}")
            
            # Save results
            output_path = Path(__file__).parent.parent / "data" / "evaluation" / "results.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "results": results,
                    "metrics": metrics,
                    "summary": {
                        "total": len(results),
                        "successful": len(successful_results),
                        "failed": len(results) - len(successful_results)
                    }
                }, f, indent=2, ensure_ascii=False)
            
            logger.info(f"\nResults saved to: {output_path}")
        else:
            logger.warning("Cannot calculate metrics: missing ground truth data")
    else:
        logger.error("No successful evaluations")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
