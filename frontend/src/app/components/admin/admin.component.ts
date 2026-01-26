import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AdminService, AdminStats, MissingDish, Dish } from '../../services/admin.service';
import { AuthService } from '../../services/auth.service';
import { DishEditorComponent, EditableDish } from '../dish-editor/dish-editor.component';
import { forkJoin } from 'rxjs';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, DishEditorComponent],
  templateUrl: './admin.component.html',
  styleUrls: ['./admin.component.scss']
})
export class AdminComponent implements OnInit {
  // Tab state
  activeTab:  'dishes' | 'missing' = 'missing';
  
  // Stats
  stats: AdminStats | null = null;
  
  // Missing dishes
  missingDishes: MissingDish[] = [];
  loading = true;
  
  // All dishes
  allDishes: Dish[] = [];
  filteredDishes:  Dish[] = [];
  dishesLoading = false;
  searchQuery = '';
  
  // Filters
  selectedCountry = '';
  sortBy = 'query_count';
  
  // Loading actions
  loadingAction: { [key: string]:  boolean } = {};
  
  // Editor state
  editorOpen = false;
  dishToEdit: EditableDish | null = null;
  editorLoading = false;
  isEditMode = false;
  editingDishId: number | null = null;
  editingMissingDish: MissingDish | null = null;  // Track which missing dish we're editing

  constructor(
    private adminService: AdminService,
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadStats();
    this.loadMissingDishes();
    this.loadAllDishes();
  }

  // ==========================================
  // TAB SWITCHING
  // ==========================================
  
  switchTab(tab: 'dishes' | 'missing'): void {
    this.activeTab = tab;
    if (tab === 'dishes') {
      this.loadAllDishes();
    } else {
      this.loadMissingDishes();
    }
  }

  // ==========================================
  // STATS
  // ==========================================
  
  loadStats(): void {
    this.adminService.getStats().subscribe({
      next:  (stats) => {
        this.stats = stats;
      },
      error:  (error) => {
        console.error('Error loading stats:', error);
      }
    });
  }

  // ==========================================
  // ALL DISHES
  // ==========================================
  
  loadAllDishes(): void {
    this.dishesLoading = true;
    this.adminService.getAllDishes(this.selectedCountry || undefined).subscribe({
      next: (response) => {
        this.allDishes = response.dishes;
        this.filterDishes();
        this.dishesLoading = false;
      },
      error: (error) => {
        console.error('Error loading dishes:', error);
        this.dishesLoading = false;
      }
    });
  }

  filterDishes(): void {
    let filtered = [...this.allDishes];
    
    if (this.searchQuery.trim()) {
      const query = this.searchQuery.toLowerCase();
      filtered = filtered.filter(d => 
        d.dish_name.toLowerCase().includes(query)
      );
    }
    
    this.filteredDishes = filtered;
  }

  // Helpers for dish display
  getDishWeight(dish:  Dish): number {
    return dish['weight (g)'] || (dish as any).weight_g || 0;
  }

  getDishCarbs(dish: Dish): number {
    if ((dish as any).carbs !== undefined) {
      return (dish as any).carbs;
    }
    // Calculate from ingredients
    const ingredients = this.parseIngredients(dish);
    return ingredients.reduce((sum, ing) => sum + (ing.carbs || 0), 0);
  }

  getDishProtein(dish:  Dish): number {
    if ((dish as any).protein !== undefined) {
      return (dish as any).protein;
    }
    const ingredients = this.parseIngredients(dish);
    return ingredients.reduce((sum, ing) => sum + (ing.protein || 0), 0);
  }

  getDishFat(dish: Dish): number {
    if ((dish as any).fat !== undefined) {
      return (dish as any).fat;
    }
    const ingredients = this.parseIngredients(dish);
    return ingredients.reduce((sum, ing) => sum + (ing.fat || 0), 0);
  }

  getIngredientCount(dish: Dish): number {
    return this.parseIngredients(dish).length;
  }

  getIngredientsPreview(dish: Dish): string {
    const ingredients = this.parseIngredients(dish);
    const names = ingredients.slice(0, 3).map(ing => ing.name.split(',')[0]);
    const preview = names.join(', ');
    if (ingredients.length > 3) {
      return preview + ` ...+${ingredients.length - 3} more`;
    }
    return preview;
  }

  parseIngredients(dish:  Dish): any[] {
    try {
      if (typeof dish.ingredients === 'string') {
        return JSON.parse(dish.ingredients);
      }
      return dish.ingredients || [];
    } catch {
      return [];
    }
  }

  // ==========================================
  // MISSING DISHES
  // ==========================================
  
  loadMissingDishes(): void {
    this.loading = true;
    this.adminService.getMissingDishes(this.selectedCountry, this.sortBy).subscribe({
      next: (response) => {
        this.missingDishes = response.missing_dishes;
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading missing dishes:', error);
        this.loading = false;
      }
    });
  }

  // ==========================================
  // FILTERS
  // ==========================================
  
  onCountryChange(): void {
    if (this.activeTab === 'dishes') {
      this.loadAllDishes();
    } else {
      this.loadMissingDishes();
    }
  }

  onSortChange(): void {
    this.loadMissingDishes();
  }

  // ==========================================
  // EDITOR - NEW DISH
  // ==========================================
  
  openEditorForNewDish(): void {
    this.isEditMode = false;
    this.editingDishId = null;
    this.dishToEdit = {
      dish_name: '',
      country: this.selectedCountry || 'Lebanon',
      ingredients:  []
    };
    this.editorOpen = true;
  }

  // ==========================================
  // EDITOR - EDIT EXISTING DISH
  // ==========================================
  
  editDish(dish:  Dish): void {
    this.isEditMode = true;
    this.editingDishId = dish.dish_id;
    
    const ingredients = this.parseIngredients(dish);
    
    this.dishToEdit = {
      dish_name: dish.dish_name,
      country: dish.country,
      ingredients: ingredients.map(ing => ({
        usda_fdc_id: ing.usda_fdc_id,
        name:  ing.name,
        weight_g:  ing.weight_g,
        calories: ing.calories || 0,
        carbs:  ing.carbs || 0,
        protein: ing.protein || 0,
        fat: ing.fat || 0
      }))
    };
    
    this.editorOpen = true;
  }

  // ==========================================
  // EDITOR - MISSING DISH
  // ==========================================
  
  openEditorForMissingDish(dish: MissingDish): void {
    this.editorLoading = true;
    this.isEditMode = false;
    this.editingDishId = null;
    this.editingMissingDish = dish;  // Store the missing dish we're editing
    
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
              name: usdaResult.description,
              weight_g: ing.weight_g,
              calories: Math.round(nutrition.calories * factor * 10) / 10,
              carbs:  Math.round(nutrition.carbs * factor * 10) / 10,
              protein: Math.round(nutrition.protein * factor * 10) / 10,
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
          ingredients:  ingredientsWithNutrition
        };
        
        this.editorOpen = true;
        this.editorLoading = false;
      },
      error: (error) => {
        console.error('Error searching USDA:', error);
        alert('Error loading ingredient data. Please try again.');
        this.editorLoading = false;
      }
    });
  }

  closeEditor(): void {
    this.editorOpen = false;
    this.dishToEdit = null;
    this.isEditMode = false;
    this.editingDishId = null;
    this.editingMissingDish = null;
  }

  // ==========================================
  // SAVE / UPDATE DISH
  // ==========================================
  
  saveDish(dish: EditableDish): void {
    const dishCreate = {
      dish_name: dish.dish_name,
      country: dish.country,
      weight_g: dish.ingredients.reduce((sum, ing) => sum + ing.weight_g, 0),
      ingredients: dish.ingredients
    };

    // If saving from a missing dish, use addMissingDishToDatabase to update status
    if (this.editingMissingDish) {
      // Pass the edited dish data to the endpoint
      this.adminService.addMissingDishToDatabase(dish.dish_name, dish.country, dishCreate).subscribe({
        next: () => {
          alert('✅ Dish added to database successfully!');
          this.closeEditor();
          this.loadStats();
          this.loadAllDishes();
          this.loadMissingDishes();  // This will refresh and filter out "added" dishes
        },
        error: (error) => {
          console.error('Error adding dish to database:', error);
          alert(`❌ Error: ${error.error?.detail || 'Failed to add dish to database'}`);
        }
      });
    } else {
      // Regular dish creation
      this.adminService.createDish(dishCreate).subscribe({
        next: () => {
          alert('✅ Dish saved successfully!');
          this.closeEditor();
          this.loadStats();
          this.loadAllDishes();
          this.loadMissingDishes();
        },
        error:  (error) => {
          console.error('Error saving dish:', error);
          alert(`❌ Error:  ${error.error?.detail || 'Failed to save dish'}`);
        }
      });
    }
  }

  updateDish(dish:  EditableDish): void {
    if (! this.editingDishId) return;
    
    const dishUpdate = {
      dish_name: dish.dish_name,
      country: dish.country,
      weight_g: dish.ingredients.reduce((sum, ing) => sum + ing.weight_g, 0),
      ingredients:  dish.ingredients
    };

    this.adminService.updateDish(this.editingDishId, dishUpdate).subscribe({
      next: () => {
        alert('✅ Dish updated successfully!');
        this.closeEditor();
        this.loadStats();
        this.loadAllDishes();
      },
      error:  (error) => {
        console.error('Error updating dish:', error);
        alert(`❌ Error: ${error.error?.detail || 'Failed to update dish'}`);
      }
    });
  }

  // ==========================================
  // DELETE DISH
  // ==========================================
  
  deleteDish(dish: Dish): void {
    if (! confirm(`Delete "${dish.dish_name}"?  This cannot be undone.`)) {
      return;
    }

    this.adminService.deleteDish(dish.dish_id).subscribe({
      next:  () => {
        alert('✅ Dish deleted successfully! ');
        this.loadStats();
        this.loadAllDishes();
      },
      error: (error) => {
        console.error('Error deleting dish:', error);
        alert(`❌ Error: ${error.error?.detail || 'Failed to delete dish'}`);
      }
    });
  }

  // ==========================================
  // MISSING DISH ACTIONS
  // ==========================================
  
  dismissDish(dish: MissingDish): void {
    if (! confirm(`Dismiss "${dish.dish_name}"? This won't add it to the database.`)) {
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

  isLoading(dish:  MissingDish): boolean {
    const key = `${dish.dish_name}_${dish.country}`;
    return this.loadingAction[key] || false;
  }

  // ==========================================
  // UTILITIES
  // ==========================================
  
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