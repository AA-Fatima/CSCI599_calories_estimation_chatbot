"""Convert USDA JSON files to SQLite database."""
import json
import sqlite3
import os
from pathlib import Path

# Paths
BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
DB_PATH = DATA_DIR / "usda. db"
FOUNDATION_PATH = DATA_DIR / "USDA_foundation. json"
SR_LEGACY_PATH = DATA_DIR / "USDA_sr_legacy.json"

def create_database():
    """Create SQLite database from USDA JSON files."""
    
    # Remove old database if exists
    if DB_PATH.exists():
        os.remove(DB_PATH)
        print(f"Removed old database")
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tables
    cursor. execute('''
        CREATE TABLE foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fdc_id INTEGER,
            description TEXT,
            description_lower TEXT,
            calories REAL DEFAULT 0,
            protein REAL DEFAULT 0,
            carbs REAL DEFAULT 0,
            fat REAL DEFAULT 0,
            source TEXT
        )
    ''')
    
    # Create index for fast searching
    cursor.execute('CREATE INDEX idx_description_lower ON foods(description_lower)')
    cursor.execute('CREATE INDEX idx_fdc_id ON foods(fdc_id)')
    
    print("Created database tables")
    
    # Load Foundation Foods
    if FOUNDATION_PATH.exists():
        print(f"Loading Foundation Foods from {FOUNDATION_PATH}...")
        with open(FOUNDATION_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        foods = data.get('FoundationFoods', []) or data.get('foods', [])
        insert_foods(cursor, foods, 'foundation')
        print(f"   ✅ Inserted {len(foods)} foundation foods")
    
    # Load SR Legacy Foods
    if SR_LEGACY_PATH. exists():
        print(f"Loading SR Legacy Foods from {SR_LEGACY_PATH}...")
        with open(SR_LEGACY_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        foods = data. get('SRLegacyFoods', []) or data.get('foods', [])
        insert_foods(cursor, foods, 'sr_legacy')
        print(f"   ✅ Inserted {len(foods)} legacy foods")
    
    conn.commit()
    
    # Check total
    cursor.execute('SELECT COUNT(*) FROM foods')
    total = cursor.fetchone()[0]
    print(f"\n📊 Total foods in database: {total}")
    
    # Check file size
    size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
    print(f"📁 Database size:  {size_mb:. 1f} MB")
    
    conn. close()
    print(f"\n✅ Database created at: {DB_PATH}")


def insert_foods(cursor, foods, source):
    """Insert foods into database."""
    for food in foods: 
        fdc_id = food.get('fdcId', 0)
        description = food.get('description', '')
        
        # Extract nutrition
        calories, protein, carbs, fat = extract_nutrition(food)
        
        cursor.execute('''
            INSERT INTO foods (fdc_id, description, description_lower, calories, protein, carbs, fat, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (fdc_id, description, description. lower(), calories, protein, carbs, fat, source))


def extract_nutrition(food):
    """Extract nutrition values from USDA food item."""
    calories = 0.0
    protein = 0.0
    carbs = 0.0
    fat = 0.0
    
    food_nutrients = food.get('foodNutrients', [])
    
    for nutrient_item in food_nutrients: 
        nutrient_info = nutrient_item.get('nutrient', {})
        name = nutrient_info.get('name', '').lower()
        value = nutrient_item.get('amount', 0.0) or 0.0
        
        if not name: 
            name = nutrient_item.get('nutrientName', '').lower()
            value = nutrient_item.get('value', 0.0) or 0.0
        
        # Energy/Calories
        if 'energy' in name: 
            unit = nutrient_info.get('unitName', '').lower()
            if 'kcal' in unit or (value < 1000 and value > 0):
                calories = float(value)
        
        # Carbohydrates
        elif 'carbohydrate' in name and 'by difference' in name: 
            carbs = float(value)
        
        # Protein
        elif name == 'protein': 
            protein = float(value)
        
        # Fat
        elif 'total lipid' in name or name == 'total lipid (fat)':
            fat = float(value)
    
    return calories, protein, carbs, fat


if __name__ == '__main__':
    create_database()