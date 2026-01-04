import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { AdminService } from '../../services/admin.service';

@Component({
  selector: 'app-admin-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './admin-login.component.html',
  styleUrls: ['./admin-login.component.scss']
})
export class AdminLoginComponent {
  password: string = '';
  errorMessage: string = '';
  isLoading: boolean = false;

  constructor(
    private authService: AuthService,
    private adminService: AdminService,
    private router: Router
  ) {}

  onSubmit(): void {
    if (!this.password) {
      this.errorMessage = 'Please enter a password';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    // Store password temporarily
    this.authService.setPassword(this.password);

    // Test password by calling dedicated verify endpoint
    this.adminService.verifyPassword().subscribe({
      next: () => {
        // Password is correct, navigate to admin dashboard
        this.isLoading = false;
        this.router.navigate(['/admin/dashboard']);
      },
      error: (error) => {
        // Password is incorrect, clear it
        this.authService.clearPassword();
        this.isLoading = false;
        
        if (error.status === 401) {
          this.errorMessage = 'Invalid password';
        } else {
          this.errorMessage = 'Authentication failed. Please try again.';
        }
      }
    });
  }
}
