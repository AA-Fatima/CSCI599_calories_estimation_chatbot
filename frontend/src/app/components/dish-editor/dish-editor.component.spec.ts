import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DishEditorComponent } from './dish-editor.component';

describe('DishEditorComponent', () => {
  let component: DishEditorComponent;
  let fixture: ComponentFixture<DishEditorComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DishEditorComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(DishEditorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
