import { Ingredient } from './chat.model';

export interface Dish {
  dish_id: number;
  dish_name: string;
  weight_g: number;
  calories: number;
  ingredients: Ingredient[];
  country: string;
  date_accessed?: string;
}

export interface DishCreate {
  dish_name: string;
  weight_g: number;
  country: string;
  ingredients: Ingredient[];
}

export interface MissingDish {
  dish_name: string;
  dish_name_arabic?: string;
  country: string;
  query_text: string;
  gpt_response: any;
  ingredients: Array<{ name: string; weight_g: number }>;
  query_count: number;
  first_queried: string;
  last_queried: string;
}

export interface AdminStats {
  total_dishes: number;
  missing_dishes_count: number;
  queries_today: number;
  countries: string[];
}
