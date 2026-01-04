"""Comparison/Evaluation API routes."""
from fastapi import APIRouter, HTTPException
from app.models.schemas import ComparisonReport
from app.evaluation.comparator import comparator
from app.evaluation.report_generator import report_generator

router = APIRouter(prefix="/comparison", tags=["comparison"])


@router.post("/run", response_model=ComparisonReport)
async def run_comparison():
    """
    Run comparison evaluation.
    
    Returns:
        Complete comparison report
    """
    try:
        # Load test queries
        queries = comparator.load_test_queries()
        
        if not queries:
            raise HTTPException(status_code=404, detail="No test queries found")
        
        # Run comparison
        results = comparator.run_comparison(queries)
        
        # Generate report
        report = report_generator.generate_report(results)
        
        return report
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-queries")
async def get_test_queries():
    """
    Get list of test queries.
    
    Returns:
        List of test queries
    """
    queries = comparator.load_test_queries()
    return {"queries": [q.dict() for q in queries]}
