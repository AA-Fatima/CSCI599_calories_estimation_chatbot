import { NutritionTotals } from './chat.model';

export interface ComparisonResult {
  query: string;
  expected: NutritionTotals;
  chatbot: NutritionTotals;
  gpt: NutritionTotals;
  deepseek: NutritionTotals;
}

export interface ComparisonMetrics {
  mae: number;
  rmse: number;
  mape: number;
  accuracy_10_percent: number;
  accuracy_20_percent: number;
}

export interface ComparisonReport {
  results: ComparisonResult[];
  chatbot_metrics: ComparisonMetrics;
  gpt_metrics: ComparisonMetrics;
  deepseek_metrics: ComparisonMetrics;
  summary: string;
}
