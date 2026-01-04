"""Metrics calculation for comparison evaluation."""
import numpy as np
from typing import List
from app.models.schemas import ComparisonMetrics, NutritionTotals


def calculate_metrics(
    expected_values: List[float],
    predicted_values: List[float]
) -> ComparisonMetrics:
    """
    Calculate evaluation metrics.
    
    Args:
        expected_values: Expected calorie values
        predicted_values: Predicted calorie values
        
    Returns:
        Calculated metrics
    """
    expected = np.array(expected_values)
    predicted = np.array(predicted_values)
    
    # Mean Absolute Error
    mae = np.mean(np.abs(expected - predicted))
    
    # Root Mean Square Error
    rmse = np.sqrt(np.mean((expected - predicted) ** 2))
    
    # Mean Absolute Percentage Error
    mape = np.mean(np.abs((expected - predicted) / expected)) * 100
    
    # Accuracy within 10%
    within_10 = np.sum(np.abs(expected - predicted) / expected <= 0.1)
    accuracy_10 = (within_10 / len(expected)) * 100
    
    # Accuracy within 20%
    within_20 = np.sum(np.abs(expected - predicted) / expected <= 0.2)
    accuracy_20 = (within_20 / len(expected)) * 100
    
    return ComparisonMetrics(
        mae=float(mae),
        rmse=float(rmse),
        mape=float(mape),
        accuracy_10_percent=float(accuracy_10),
        accuracy_20_percent=float(accuracy_20)
    )
