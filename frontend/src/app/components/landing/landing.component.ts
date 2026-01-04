import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { CountryService } from '../../services/country.service';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatAutocompleteModule } from '@angular/material/autocomplete'; 
@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [CommonModule, FormsModule, MatFormFieldModule, MatInputModule, MatAutocompleteModule],
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.scss'
})
export class LandingComponent implements OnInit {
  countries: string[] = [];
  selectedCountry: string = '';
  loading = false;
  features = [
    { icon: '🍽️', title: 'Arabic Cuisine', description: 'Specialized in dishes from Lebanon, Egypt, Saudi Arabia, and more' }, 
    { icon: '🌍', title: 'Smart AI', description: 'Understands English, Arabic, and Franco-Arabic (Arabizi)' },
    { icon: '📊', title: 'Accurate Data', description: 'Based on USDA database and verified nutritional information' },
    { icon: '✏️', title: 'Detailed Breakdown', description: 'Show nutritional information and detailed ingredients' }
  ];
  constructor(
    private countryService: CountryService,
    private router: Router
  ) {}

  ngOnInit() {
    this.loadCountries();
  }

  loadCountries() {
    this.loading = true;
    this.countryService.getCountries().subscribe({
      next: (response) => {
        this.countries = response.countries;
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading countries:', error);
        this.loading = false;
      }
    });
  }
get filteredCountries(): string[] {
  return this.countries.filter(country =>
    country.toLowerCase().includes(this.selectedCountry.toLowerCase())
  );
}

  startChat() {
    if (this.selectedCountry) {
      this.router.navigate(['/chatbot'], { 
        queryParams: { country: this.selectedCountry } 
      });
    }
  }
}
