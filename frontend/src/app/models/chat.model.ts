export interface Ingredient {
  name: string;
  weight_g: number;
  usda_fdc_id?: number;
  calories: number;
  carbs: number;
  protein: number;
  fat: number;
}

export interface NutritionTotals {
  calories: number;
  carbs: number;
  protein: number;
  fat: number;
}

export interface ChatMessage {
  message: string;
  session_id?: string;
  country?: string;
}

export interface ChatResponse {
  session_id: string;
  dish_name: string;
  dish_name_arabic?: string;
  ingredients: Ingredient[];
  totals: NutritionTotals;
  source: 'dataset' | 'ai_estimated';
  message: string;
}

export interface Message {
  type: 'user' | 'bot';
  content: string;
  response?: ChatResponse;
  timestamp: Date;
}
