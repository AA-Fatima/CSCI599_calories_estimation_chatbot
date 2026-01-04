import { Component, Input, Output, EventEmitter, OnInit, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService } from '../../services/admin.service';

export interface EditableIngredient {
  usda_fdc_id?:  number;
  name: string;
  weight_g: number;
  calories: number;
  carbs: number;
  protein:  number;
  fat: number;
}

export interface EditableDish {
  dish_name: string;
  country: string;
  ingredients:  EditableIngredient[];
}

@Component({
  selector:  'app-dish-editor',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './dish-editor.component.html',
  styleUrls: ['./dish-editor.component.scss']
})
export class DishEditorComponent implements OnInit, OnChanges {
  @Input() dish: EditableDish | null = null;
  @Input() isOpen = false;
  @Output() close = new EventEmitter<void>();
  @Output() save = new EventEmitter<EditableDish>();

  editedDish: EditableDish = {
    dish_name: '',
    country: '',
    ingredients: []
  };

  searchQuery = '';
  searchResults: any = null;
  searching = false;
  selectedWeight = 100;

  constructor(private adminService: AdminService) {}

  ngOnInit(): void {
    this.loadDishData();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['dish'] && changes['dish'].currentValue) {
      this.loadDishData();
    }
  }

  loadDishData(): void {
    if (this.dish) {
      // Deep copy to avoid mutating the original
      this.editedDish = JSON.parse(JSON.stringify(this.dish));
      console.log('📝 Loaded dish data:', this.editedDish);
    } else {
      // Reset for new dish
      this.editedDish = {
        dish_name: '',
        country: '',
        ingredients: []
      };
    }
  }

  searchUSDA(): void {
    if (!this.searchQuery.trim()) return;

    this.searching = true;
    this.adminService.searchUSDA(this.searchQuery).subscribe({
      next: (result) => {
        this.searchResults = result;
        this.searching = false;
      },
      error: (error) => {
        console.error('Error searching USDA:', error);
        alert('Error searching USDA database');
        this.searching = false;
      }
    });
  }

  addIngredientFromSearch(): void {
    if (!this.searchResults || !this.searchResults.found) return;

    const nutrition = this.searchResults.nutrition_per_100g;
    const factor = this.selectedWeight / 100;

    const newIngredient:  EditableIngredient = {
      usda_fdc_id: this.searchResults.fdc_id,
      name: this.searchResults.description,
      weight_g: this.selectedWeight,
      calories: Math.round(nutrition.calories * factor * 10) / 10,
      carbs: Math.round(nutrition.carbs * factor * 10) / 10,
      protein: Math.round(nutrition.protein * factor * 10) / 10,
      fat: Math.round(nutrition.fat * factor * 10) / 10
    };

    this.editedDish.ingredients.push(newIngredient);
    
    // Reset search
    this.searchQuery = '';
    this.searchResults = null;
    this.selectedWeight = 100;
  }

  removeIngredient(index: number): void {
    if (confirm('Remove this ingredient?')) {
      this.editedDish.ingredients.splice(index, 1);
    }
  }

  updateIngredientWeight(ingredient: EditableIngredient, newWeight: number): void {
    if (newWeight <= 0) return;
    
    const oldWeight = ingredient.weight_g;
    const factor = newWeight / oldWeight;

    ingredient.weight_g = newWeight;
    ingredient.calories = Math.round(ingredient.calories * factor * 10) / 10;
    ingredient.carbs = Math.round(ingredient.carbs * factor * 10) / 10;
    ingredient.protein = Math.round(ingredient.protein * factor * 10) / 10;
    ingredient.fat = Math.round(ingredient.fat * factor * 10) / 10;
  }

  getTotalCalories(): number {
    return this.editedDish.ingredients.reduce((sum, ing) => sum + ing.calories, 0);
  }

  getTotalWeight(): number {
    return this.editedDish.ingredients.reduce((sum, ing) => sum + ing.weight_g, 0);
  }

  onSave(): void {
    if (!this.editedDish.dish_name.trim()) {
      alert('Please enter a dish name');
      return;
    }

    if (!this.editedDish.country.trim()) {
      alert('Please select a country');
      return;
    }

    if (this.editedDish.ingredients.length === 0) {
      alert('Please add at least one ingredient');
      return;
    }

    this.save.emit(this.editedDish);
  }

  onClose(): void {
    if (confirm('Close without saving changes?')) {
      this.close.emit();
    }
  }
}