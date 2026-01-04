import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly STORAGE_KEY = 'admin_password';

  constructor() {}

  /**
   * Store password in sessionStorage.
   * 
   * NOTE: For a production application, this would use JWT tokens instead of storing
   * the password directly. This simple approach is acceptable for a thesis project
   * but should be upgraded for production use.
   */
  setPassword(password: string): void {
    sessionStorage.setItem(this.STORAGE_KEY, password);
  }

  getPassword(): string | null {
    return sessionStorage.getItem(this.STORAGE_KEY);
  }

  clearPassword(): void {
    sessionStorage.removeItem(this.STORAGE_KEY);
  }

  isAuthenticated(): boolean {
    return !!this.getPassword();
  }
}
