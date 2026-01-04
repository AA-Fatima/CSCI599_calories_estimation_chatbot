import { Injectable } from '@angular/core';
import { HttpClient, HttpParams, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { AuthService } from './auth.service';

export interface AdminStats {
  total_dishes:  number;
  missing_dishes_count: number;
  queries_today: number;
  countries: string[];
}

export interface MissingDish {
  dish_name: string;
  dish_name_arabic:  string | null;
  country: string;
  query_text: string;
  gpt_response: any;
  ingredients: Array<{
    name: string;
    weight_g: number;
  }>;
  query_count: number;
  first_queried: string;
  last_queried: string;
}

export interface MissingDishesResponse {
  missing_dishes: MissingDish[];
  total:  number;
}

export interface Dish {
  dish_id: number;
  dish_name: string;
  'weight (g)': number;
  calories: number;
  ingredients: string;
  country: string;
  date_accessed: string;
}

export interface IngredientCreate {
  usda_fdc_id?:  number;
  name: string;
  weight_g: number;
  calories: number;
  carbs: number;
  protein:  number;
  fat: number;
}

export interface DishCreate {
  dish_name: string;
  country: string;
  weight_g: number;
  ingredients: IngredientCreate[];
}

@Injectable({
  providedIn: 'root'
})
export class AdminService {
  private apiUrl = `${environment.apiUrl}/admin`;

  constructor(
    private http: HttpClient,
    private authService: AuthService
  ) {}

  private getHeaders(): HttpHeaders {
    const password = this.authService.getPassword();
    if (password) {
      return new HttpHeaders({
        'X-Admin-Password': password
      });
    }
    return new HttpHeaders();
  }

  verifyPassword(): Observable<{ authenticated: boolean }> {
    return this.http.post<{ authenticated: boolean }>(`${this.apiUrl}/verify`, null, {
      headers: this.getHeaders()
    });
  }

  getStats(): Observable<AdminStats> {
    return this.http.get<AdminStats>(`${this.apiUrl}/stats`, {
      headers: this.getHeaders()
    });
  }

  getMissingDishes(country?:  string, sortBy:  string = 'query_count'): Observable<MissingDishesResponse> {
    let params = new HttpParams().set('sort_by', sortBy);
    if (country) {
      params = params.set('country', country);
    }
    return this.http.get<MissingDishesResponse>(`${this.apiUrl}/missing-dishes`, {
      params,
      headers: this.getHeaders()
    });
  }

  addMissingDishToDatabase(dishName: string, country: string): Observable<any> {
    const params = new HttpParams().set('country', country);
    return this.http.post(
      `${this.apiUrl}/missing-dishes/${encodeURIComponent(dishName)}/add-to-database`,
      null,
      {
        params,
        headers: this.getHeaders()
      }
    );
  }

  deleteMissingDish(dishName: string, country: string): Observable<any> {
    const params = new HttpParams().set('country', country);
    return this.http.delete(
      `${this.apiUrl}/missing-dishes/${encodeURIComponent(dishName)}`,
      {
        params,
        headers: this.getHeaders()
      }
    );
  }

  getAllDishes(country?: string): Observable<{ dishes: Dish[], total: number }> {
    let params = new HttpParams();
    if (country) {
      params = params.set('country', country);
    }
    return this.http.get<{ dishes: Dish[], total: number }>(`${this.apiUrl}/dishes`, {
      params,
      headers: this.getHeaders()
    });
  }

createDish(dish: DishCreate): Observable<any> {
  return this.http.post(`${this.apiUrl}/dishes`, dish, {
    headers: this.getHeaders()  // ← Add this
  });
}

updateDish(dishId: number, dish: DishCreate): Observable<any> {
  return this.http.put(`${this.apiUrl}/dishes/${dishId}`, dish, {
    headers: this.getHeaders()  // ← Add this
  });
}

deleteDish(dishId:  number): Observable<any> {
  return this.http.delete(`${this.apiUrl}/dishes/${dishId}`, {
    headers: this.getHeaders()  // ← Add this
  });
}

  searchUSDA(query: string, threshold: number = 70): Observable<any> {
    const params = new HttpParams()
      .set('query', query)
      .set('threshold', threshold.toString());
    return this.http.get(`${this.apiUrl}/usda/search`, {
      params,
      headers: this.getHeaders()
    });
  }
}