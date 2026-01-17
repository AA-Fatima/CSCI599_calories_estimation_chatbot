"""Evaluation metrics for calorie estimation accuracy."""
import numpy as np
from typing import List, Dict, Tuple
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    mean_absolute_percentage_error
)
from loguru import logger


class EvaluationMetrics:
    """Calculate comprehensive evaluation metrics."""
    
    @staticmethod
    def calculate_accuracy_metrics(
        predictions: List[float],
        ground_truth: List[float]
    ) -> Dict[str, float]:
        """
        Calculate accuracy metrics for calorie predictions.
        
        Args:
            predictions: List of predicted calorie values
            ground_truth: List of ground truth calorie values
            
        Returns:
            Dictionary with metric names and values
        """
        predictions = np.array(predictions)
        ground_truth = np.array(ground_truth)
        
        # Remove any invalid values
        valid_mask = np.isfinite(predictions) & np.isfinite(ground_truth)
        predictions = predictions[valid_mask]
        ground_truth = ground_truth[valid_mask]
        
        if len(predictions) == 0:
            logger.warning("No valid predictions for metric calculation")
            return {
                "MAE": np.nan,
                "RMSE": np.nan,
                "MAPE": np.nan,
                "R²": np.nan,
                "Mean Error": np.nan,
                "Std Error": np.nan
            }
        
        mae = mean_absolute_error(ground_truth, predictions)
        rmse = np.sqrt(mean_squared_error(ground_truth, predictions))
        
        # MAPE calculation (handle division by zero)
        mape = np.mean(np.abs((ground_truth - predictions) / (ground_truth + 1e-10))) * 100
        
        r2 = r2_score(ground_truth, predictions)
        mean_error = np.mean(predictions - ground_truth)
        std_error = np.std(predictions - ground_truth)
        
        return {
            "MAE": float(mae),
            "RMSE": float(rmse),
            "MAPE": float(mape),
            "R²": float(r2),
            "Mean Error": float(mean_error),
            "Std Error": float(std_error),
            "N": len(predictions)
        }
    
    @staticmethod
    def calculate_search_metrics(
        results: List[Dict],
        ground_truth: List[Dict]
    ) -> Dict[str, float]:
        """
        Calculate search accuracy metrics.
        
        Args:
            results: List of search results with dish names
            ground_truth: List of expected dish names
            
        Returns:
            Dictionary with search metrics
        """
        if len(results) != len(ground_truth):
            logger.warning("Results and ground truth length mismatch")
            return {}
        
        exact_matches = sum(
            1 for r, gt in zip(results, ground_truth)
            if r.get("dish_name", "").lower() == gt.get("expected_dish", "").lower()
        )
        
        total = len(results)
        accuracy = exact_matches / total if total > 0 else 0.0
        
        # Calculate average similarity for matches
        similarities = [
            r.get("similarity", 0.0) for r in results
            if r.get("similarity", 0.0) > 0
        ]
        avg_similarity = np.mean(similarities) if similarities else 0.0
        
        return {
            "Exact Match Accuracy": accuracy,
            "Exact Matches": exact_matches,
            "Total Queries": total,
            "Average Similarity": float(avg_similarity)
        }
    
    @staticmethod
    def calculate_ingredient_accuracy(
        predicted_ingredients: List[List[str]],
        ground_truth_ingredients: List[List[str]]
    ) -> Dict[str, float]:
        """
        Calculate ingredient matching accuracy.
        
        Args:
            predicted_ingredients: List of predicted ingredient lists
            ground_truth_ingredients: List of ground truth ingredient lists
            
        Returns:
            Dictionary with ingredient accuracy metrics
        """
        if len(predicted_ingredients) != len(ground_truth_ingredients):
            logger.warning("Predicted and ground truth ingredient length mismatch")
            return {}
        
        precisions = []
        recalls = []
        f1_scores = []
        
        for pred, gt in zip(predicted_ingredients, ground_truth_ingredients):
            pred_set = set(ing.lower() for ing in pred)
            gt_set = set(ing.lower() for ing in gt)
            
            if len(pred_set) == 0 and len(gt_set) == 0:
                continue
            
            tp = len(pred_set & gt_set)
            fp = len(pred_set - gt_set)
            fn = len(gt_set - pred_set)
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            
            precisions.append(precision)
            recalls.append(recall)
            f1_scores.append(f1)
        
        return {
            "Mean Precision": float(np.mean(precisions)) if precisions else 0.0,
            "Mean Recall": float(np.mean(recalls)) if recalls else 0.0,
            "Mean F1 Score": float(np.mean(f1_scores)) if f1_scores else 0.0,
            "N": len(precisions)
        }
    
    @staticmethod
    def calculate_percentage_within_range(
        predictions: List[float],
        ground_truth: List[float],
        tolerance_percent: float = 10.0
    ) -> Dict[str, float]:
        """
        Calculate percentage of predictions within tolerance range.
        
        Args:
            predictions: List of predicted values
            ground_truth: List of ground truth values
            tolerance_percent: Tolerance percentage (default 10%)
            
        Returns:
            Dictionary with percentage metrics
        """
        predictions = np.array(predictions)
        ground_truth = np.array(ground_truth)
        
        valid_mask = np.isfinite(predictions) & np.isfinite(ground_truth) & (ground_truth > 0)
        predictions = predictions[valid_mask]
        ground_truth = ground_truth[valid_mask]
        
        if len(predictions) == 0:
            return {"Within 10%": 0.0, "Within 20%": 0.0, "Within 30%": 0.0}
        
        errors = np.abs(predictions - ground_truth) / ground_truth * 100
        
        within_10 = np.sum(errors <= 10.0) / len(errors) * 100
        within_20 = np.sum(errors <= 20.0) / len(errors) * 100
        within_30 = np.sum(errors <= 30.0) / len(errors) * 100
        
        return {
            f"Within {tolerance_percent}%": float(within_10),
            "Within 20%": float(within_20),
            "Within 30%": float(within_30)
        }
