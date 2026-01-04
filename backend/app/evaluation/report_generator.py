"""Report generator for comparison evaluation."""
from typing import List
from app.models.schemas import ComparisonResult, ComparisonReport, ComparisonMetrics
from app.evaluation.metrics import calculate_metrics


class ReportGenerator:
    """Generate comparison reports."""
    
    def generate_report(self, results: List[ComparisonResult]) -> ComparisonReport:
        """
        Generate full comparison report.
        
        Args:
            results: List of comparison results
            
        Returns:
            Complete comparison report
        """
        # Extract calorie values
        expected = [r.expected.calories for r in results]
        chatbot = [r.chatbot.calories for r in results]
        gpt = [r.gpt.calories for r in results]
        deepseek = [r.deepseek.calories for r in results]
        
        # Calculate metrics
        chatbot_metrics = calculate_metrics(expected, chatbot)
        gpt_metrics = calculate_metrics(expected, gpt)
        deepseek_metrics = calculate_metrics(expected, deepseek)
        
        # Generate summary
        summary = self._generate_summary(chatbot_metrics, gpt_metrics, deepseek_metrics)
        
        return ComparisonReport(
            results=results,
            chatbot_metrics=chatbot_metrics,
            gpt_metrics=gpt_metrics,
            deepseek_metrics=deepseek_metrics,
            summary=summary
        )
    
    def _generate_summary(
        self,
        chatbot_metrics: ComparisonMetrics,
        gpt_metrics: ComparisonMetrics,
        deepseek_metrics: ComparisonMetrics
    ) -> str:
        """Generate text summary of comparison."""
        lines = []
        lines.append("=== COMPARISON SUMMARY ===")
        lines.append("")
        lines.append("Chatbot (USDA-based):")
        lines.append(f"  - MAE: {chatbot_metrics.mae:.2f} kcal")
        lines.append(f"  - RMSE: {chatbot_metrics.rmse:.2f} kcal")
        lines.append(f"  - MAPE: {chatbot_metrics.mape:.2f}%")
        lines.append(f"  - Accuracy within 10%: {chatbot_metrics.accuracy_10_percent:.1f}%")
        lines.append(f"  - Accuracy within 20%: {chatbot_metrics.accuracy_20_percent:.1f}%")
        lines.append("")
        lines.append("ChatGPT Direct:")
        lines.append(f"  - MAE: {gpt_metrics.mae:.2f} kcal")
        lines.append(f"  - RMSE: {gpt_metrics.rmse:.2f} kcal")
        lines.append(f"  - MAPE: {gpt_metrics.mape:.2f}%")
        lines.append(f"  - Accuracy within 10%: {gpt_metrics.accuracy_10_percent:.1f}%")
        lines.append(f"  - Accuracy within 20%: {gpt_metrics.accuracy_20_percent:.1f}%")
        lines.append("")
        lines.append("DeepSeek Direct:")
        lines.append(f"  - MAE: {deepseek_metrics.mae:.2f} kcal")
        lines.append(f"  - RMSE: {deepseek_metrics.rmse:.2f} kcal")
        lines.append(f"  - MAPE: {deepseek_metrics.mape:.2f}%")
        lines.append(f"  - Accuracy within 10%: {deepseek_metrics.accuracy_10_percent:.1f}%")
        lines.append(f"  - Accuracy within 20%: {deepseek_metrics.accuracy_20_percent:.1f}%")
        
        return "\n".join(lines)


# Global instance
report_generator = ReportGenerator()
