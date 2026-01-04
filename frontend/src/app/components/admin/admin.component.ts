import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AdminService, AdminStats, MissingDish } from '../../services/admin.service';
import { AuthService } from '../../services/auth.service';
import { DishEditorComponent, EditableDish } from '../dish-editor/dish-editor.component';
import { forkJoin } from 'rxjs';

@Component({
  selector:  'app-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, DishEditorComponent],
  templateUrl:  './admin.component.html',
  styleUrls: ['./admin.component.scss']
})
export class AdminComponent implements OnInit {
  stats: AdminStats | null = null;
  missingDishes: MissingDish[] = [];
  loading = true;
  
  selectedCountry = '';
  sortBy = 'query_count';
  
  loadingAction: { [key:  string]: boolean } = {};
  
  // Editor state
  editorOpen = false;
  dishToEdit: EditableDish | null = null;
  editorLoading = false;

  constructor(
    private adminService: AdminService,
      private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadStats();
    this.loadMissingDishes();
  }

  loadStats(): void {
    this.adminService.getStats().subscribe({
      next: (stats) => {
        this.stats = stats;
      },
      error: (error) => {
        console.error('Error loading stats:', error);
      }
    });
  }

  loadMissingDishes(): void {
    this.loading = true;
    this.adminService.getMissingDishes(this.selectedCountry, this.sortBy).subscribe({
      next: (response) => {
        this.missingDishes = response.missing_dishes;
        this.loading = false;
      },
      error:  (error) => {
        console.error('Error loading missing dishes:', error);
        this.loading = false;
      }
    });
  }

  onCountryChange(): void {
    this.loadMissingDishes();
  }

  onSortChange(): void {
    this.loadMissingDishes();
  }

  openEditorForMissingDish(dish: MissingDish): void {
    this.editorLoading = true;
    const searches = dish.ingredients.map(ing => 
      this.adminService.searchUSDA(ing.name)
    );

    forkJoin(searches).subscribe({
      next: (results) => {
        const ingredientsWithNutrition = dish.ingredients.map((ing, index) => {
          const usdaResult = results[index];
          
          if (usdaResult.found) {
            const nutrition = usdaResult.nutrition_per_100g;
            const factor = ing.weight_g / 100;
            
            return {
              usda_fdc_id: usdaResult.fdc_id,
              name:  usdaResult.description,
              weight_g: ing.weight_g,
              calories: Math.round(nutrition.calories * factor * 10) / 10,
              carbs: Math.round(nutrition.carbs * factor * 10) / 10,
              protein:  Math.round(nutrition.protein * factor * 10) / 10,
              fat: Math.round(nutrition.fat * factor * 10) / 10
            };
          } else {
            return {
              name: ing.name,
              weight_g: ing.weight_g,
              calories: 0,
              carbs: 0,
              protein: 0,
              fat: 0
            };
          }
        });

        this.dishToEdit = {
          dish_name: dish.dish_name,
          country: dish.country,
          ingredients: ingredientsWithNutrition
        };
        
        this.editorOpen = true;
        this.editorLoading = false;
      },
      error: (error) => {
        console.error('Error searching USDA:', error);
        alert('Error loading ingredient data.Please try again.');
        this.editorLoading = false;
      }
    });
  }

  openEditorForNewDish(): void {
    this.dishToEdit = {
      dish_name: '',
      country: this.selectedCountry || 'Lebanon',
      ingredients:  []
    };
    this.editorOpen = true;
  }

  closeEditor(): void {
    this.editorOpen = false;
    this.dishToEdit = null;
  }

  saveDish(dish: EditableDish): void {
  const dishCreate = {
    dish_name: dish.dish_name,
    country: dish.country,
    weight_g: dish.ingredients.reduce((sum, ing) => sum + ing.weight_g, 0),
    ingredients: dish.ingredients
  };

  this.adminService.createDish(dishCreate).subscribe({
    next: () => {
      alert('✅ Dish saved successfully!');
      
      // Remove from missing dishes list if it was from there
      this.missingDishes = this.missingDishes.filter(
        d => !(d.dish_name === dish.dish_name && d.country === dish.country)
      );
      
      this.closeEditor();
      this.loadStats();
      this.loadMissingDishes();  // Refresh the list from server
    },
    error: (error) => {
      console.error('Error saving dish:', error);
      alert(`❌ Error:  ${error.error?.detail || 'Failed to save dish'}`);
    }
  });
}

  addToDatabase(dish: MissingDish): void {
    if (!confirm(`Add "${dish.dish_name}" to the database?`)) {
      return;
    }

    const key = `${dish.dish_name}_${dish.country}`;
    this.loadingAction[key] = true;

    this.adminService.addMissingDishToDatabase(dish.dish_name, dish.country).subscribe({
      next: (response) => {
        alert('✅ Dish added successfully!');
        this.loadStats();
        this.loadMissingDishes();
        this.loadingAction[key] = false;
      },
      error: (error) => {
        console.error('Error adding dish:', error);
        alert(`❌ Error: ${error.error?.detail || 'Failed to add dish'}`);
        this.loadingAction[key] = false;
      }
    });
  }

  dismissDish(dish: MissingDish): void {
    if (!confirm(`Dismiss "${dish.dish_name}"?  This won't add it to the database.`)) {
      return;
    }

    const key = `${dish.dish_name}_${dish.country}`;
    this.loadingAction[key] = true;

    this.adminService.deleteMissingDish(dish.dish_name, dish.country).subscribe({
      next: () => {
        alert('Dish dismissed');
        this.loadStats();
        this.loadMissingDishes();
        this.loadingAction[key] = false;
      },
      error: (error) => {
        console.error('Error dismissing dish:', error);
        alert('Failed to dismiss dish');
        this.loadingAction[key] = false;
      }
    });
  }

  isLoading(dish: MissingDish): boolean {
    const key = `${dish.dish_name}_${dish.country}`;
    return this.loadingAction[key] || false;
  }

  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleDateString();
  }

  logout(): void {
    if (confirm('Are you sure you want to logout?')) {
      this.authService.clearPassword();
      this.router.navigate(['/admin/login']);
    }
  }
}