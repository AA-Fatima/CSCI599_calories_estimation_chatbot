import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ComparisonReport } from '../models/comparison.model';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ComparisonService {
  private apiUrl = `${environment.apiUrl}/comparison`;

  constructor(private http: HttpClient) {}

  runComparison(): Observable<ComparisonReport> {
    return this.http.post<ComparisonReport>(`${this.apiUrl}/run`, {});
  }

  getTestQueries(): Observable<any> {
    return this.http.get(`${this.apiUrl}/test-queries`);
  }
}
