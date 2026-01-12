"""
Understanding Evaluation Script - Test 2
Tests the bot's ability to understand various query formats: 
- English (normal + typos)
- Arabic (فصحى)
- Arabizi/Franco (3, 7, 5, 2)
- Dialects (Lebanese, Syrian, Egyptian, Gulf)
- Different country foods
- Mixed languages
- Spelling mistakes
"""

import pandas as pd
import requests
import time
from datetime import datetime
from pathlib import Path

# Configuration
API_URL = "http://localhost:8000/api/chat"
OUTPUT_PATH = Path("evaluation_understanding_results.xlsx")
DELAY_SECONDS = 1

# Test cases with expected dish names
TEST_CASES = [
    # ============================================
    # ENGLISH - Normal
    # ============================================
    {"query": "How many calories in hummus", "expected_dish":  "Hummus", "language": "English", "category": "Levantine"},
    {"query": "calories in tabbouleh", "expected_dish": "Tabbouleh", "language": "English", "category": "Levantine"},
    {"query": "what are the calories in shawarma", "expected_dish": "Shawarma", "language": "English", "category": "Levantine"},
    {"query": "kibbeh calories", "expected_dish": "Kibbeh", "language":  "English", "category": "Levantine"},
    {"query": "falafel nutritional info", "expected_dish": "Falafel", "language":  "English", "category": "Levantine"},
    {"query": "fattoush salad calories", "expected_dish": "Fattoush", "language":  "English", "category": "Levantine"},
    {"query": "labneh calories", "expected_dish": "Labneh", "language": "English", "category": "Levantine"},
    {"query": "how many calories in baba ghanoush", "expected_dish": "Baba Ghanoush", "language":  "English", "category": "Levantine"},
    {"query": "grape leaves stuffed calories", "expected_dish": "Warak Enab", "language": "English", "category": "Levantine"},
    {"query": "chicken tawook calories", "expected_dish": "Tawook", "language": "English", "category": "Levantine"},
    
    # ============================================
    # ENGLISH - Typos & Misspellings
    # ============================================
    {"query": "hommos calories", "expected_dish": "Hummus", "language":  "English_Typo", "category": "Levantine"},
    {"query": "humus cal", "expected_dish": "Hummus", "language": "English_Typo", "category": "Levantine"},
    {"query": "tabouleh calories", "expected_dish": "Tabbouleh", "language": "English_Typo", "category": "Levantine"},
    {"query": "tabouli salad", "expected_dish":  "Tabbouleh", "language": "English_Typo", "category": "Levantine"},
    {"query": "shawerma calories", "expected_dish": "Shawarma", "language": "English_Typo", "category": "Levantine"},
    {"query": "shawrma chicken", "expected_dish": "Shawarma", "language":  "English_Typo", "category":  "Levantine"},
    {"query":  "kebbeh calories", "expected_dish": "Kibbeh", "language": "English_Typo", "category": "Levantine"},
    {"query": "kibbe raw", "expected_dish":  "Kibbeh", "language": "English_Typo", "category": "Levantine"},
    {"query": "felafil calories", "expected_dish": "Falafel", "language": "English_Typo", "category": "Levantine"},
    {"query": "fahita chicken", "expected_dish": "Fajita", "language":  "English_Typo", "category":  "Mexican"},
    {"query": "fajita calories", "expected_dish": "Fajita", "language":  "English_Typo", "category":  "Mexican"},
    {"query": "taouk chicken", "expected_dish": "Tawook", "language":  "English_Typo", "category":  "Levantine"},
    {"query":  "tawouk calories", "expected_dish": "Tawook", "language":  "English_Typo", "category":  "Levantine"},
    {"query":  "warak enab", "expected_dish":  "Warak Enab", "language": "English_Typo", "category": "Levantine"},
    {"query": "wara2 3enab", "expected_dish": "Warak Enab", "language": "English_Typo", "category": "Levantine"},
    
    # ============================================
    # ARABIC - فصحى (MSA)
    # ============================================
    {"query": "كم سعرة حرارية في الحمص", "expected_dish": "Hummus", "language": "Arabic_MSA", "category": "Levantine"},
    {"query": "السعرات الحرارية في التبولة", "expected_dish": "Tabbouleh", "language": "Arabic_MSA", "category": "Levantine"},
    {"query": "كم سعرة في الشاورما", "expected_dish": "Shawarma", "language": "Arabic_MSA", "category":  "Levantine"},
    {"query":  "الكبة كم فيها سعرات", "expected_dish": "Kibbeh", "language":  "Arabic_MSA", "category": "Levantine"},
    {"query": "الفلافل كم كالوري", "expected_dish": "Falafel", "language": "Arabic_MSA", "category":  "Levantine"},
    {"query":  "ورق العنب كم سعرة", "expected_dish": "Warak Enab", "language":  "Arabic_MSA", "category": "Levantine"},
    {"query": "المحاشي كم فيها كالوري", "expected_dish": "Mahashi", "language":  "Arabic_MSA", "category": "Levantine"},
    {"query": "الفتوش كم سعرة حرارية", "expected_dish": "Fattoush", "language": "Arabic_MSA", "category":  "Levantine"},
    {"query":  "اللبنة كم فيها سعرات", "expected_dish": "Labneh", "language":  "Arabic_MSA", "category": "Levantine"},
    {"query": "طاووق الدجاج كم كالوري", "expected_dish": "Tawook", "language": "Arabic_MSA", "category": "Levantine"},
    
    # ============================================
    # LEBANESE DIALECT - لبناني
    # ============================================
    {"query": "ade fi b hummus", "expected_dish": "Hummus", "language":  "Lebanese", "category": "Levantine"},
    {"query": "ade calories bl tabbouleh", "expected_dish": "Tabbouleh", "language": "Lebanese", "category":  "Levantine"},
    {"query":  "el shawarma ade fiha", "expected_dish": "Shawarma", "language":  "Lebanese", "category": "Levantine"},
    {"query": "kebbe ade fiha calories", "expected_dish": "Kibbeh", "language":  "Lebanese", "category": "Levantine"},
    {"query": "falafel kam calorie", "expected_dish": "Falafel", "language": "Lebanese", "category": "Levantine"},
    {"query": "wara2 3enab ade fihon", "expected_dish": "Warak Enab", "language": "Lebanese", "category": "Levantine"},
    {"query": "fattoush ade fiha", "expected_dish": "Fattoush", "language": "Lebanese", "category": "Levantine"},
    {"query": "labneh ade calories", "expected_dish": "Labneh", "language":  "Lebanese", "category": "Levantine"},
    {"query": "taouk ade fi", "expected_dish":  "Tawook", "language": "Lebanese", "category":  "Levantine"},
    {"query":  "msa7ab ade fiha", "expected_dish": "Msabbaha", "language":  "Lebanese", "category": "Levantine"},
    
    # ============================================
    # FRANCO/ARABIZI (Numbers:  2=أ, 3=ع, 5=خ, 7=ح, 8=غ)
    # ============================================
    {"query": "7ommos ade fi", "expected_dish": "Hummus", "language": "Franco", "category": "Levantine"},
    {"query": "kam calories bl 7ommos", "expected_dish": "Hummus", "language": "Franco", "category": "Levantine"},
    {"query": "tabboule kam fi", "expected_dish":  "Tabbouleh", "language":  "Franco", "category": "Levantine"},
    {"query": "shawerma kam calorie", "expected_dish": "Shawarma", "language": "Franco", "category": "Levantine"},
    {"query": "kebbe ne2ye ade fiha", "expected_dish": "Kibbeh", "language": "Franco", "category": "Levantine"},
    {"query": "wara2 3enab kam calories", "expected_dish": "Warak Enab", "language": "Franco", "category": "Levantine"},
    {"query": "ma7ashi ade fihon", "expected_dish": "Mahashi", "language":  "Franco", "category": "Levantine"},
    {"query": "baba 8anouj calories", "expected_dish": "Baba Ghanoush", "language": "Franco", "category": "Levantine"},
    {"query": "mana2ish zatar", "expected_dish": "Manakish", "language":  "Franco", "category": "Levantine"},
    {"query": "man2oushe jebne", "expected_dish": "Manakish", "language":  "Franco", "category": "Levantine"},
    {"query": "3arayess calories", "expected_dish": "Arayes", "language": "Franco", "category":  "Levantine"},
    {"query":  "ka3ek bel simsim", "expected_dish": "Kaak", "language": "Franco", "category":  "Levantine"},
    
    # ============================================
    # EGYPTIAN DIALECT - مصري
    # ============================================
    {"query": "كام كالوري في الكشري", "expected_dish": "Koshari", "language":  "Egyptian", "category": "Egyptian"},
    {"query": "الكشري فيه كام سعرة", "expected_dish": "Koshari", "language":  "Egyptian", "category": "Egyptian"},
    {"query": "الفول المدمس كام كالوري", "expected_dish": "Ful Medames", "language": "Egyptian", "category": "Egyptian"},
    {"query":  "فول مدمس فيه كام سعرة", "expected_dish": "Ful Medames", "language":  "Egyptian", "category": "Egyptian"},
    {"query": "الطعمية فيها كام كالوري", "expected_dish": "Falafel", "language": "Egyptian", "category": "Egyptian"},
    {"query":  "ta3meya kam calorie", "expected_dish": "Falafel", "language":  "Egyptian", "category": "Egyptian"},
    {"query": "الملوخية فيها كام سعرة", "expected_dish": "Molokhia", "language": "Egyptian", "category": "Egyptian"},
    {"query": "molokheya calories", "expected_dish": "Molokhia", "language": "Egyptian", "category": "Egyptian"},
    {"query":  "محشي كرنب كام كالوري", "expected_dish": "Mahashi", "language": "Egyptian", "category": "Egyptian"},
    {"query":  "الشاورما كام سعرة", "expected_dish": "Shawarma", "language": "Egyptian", "category": "Levantine"},
    {"query": "فتة كام كالوري", "expected_dish": "Fatteh", "language": "Egyptian", "category":  "Egyptian"},
    {"query": "بسبوسة كام سعرة", "expected_dish":  "Basbousa", "language": "Egyptian", "category":  "Egyptian"},
    
    # ============================================
    # SYRIAN DIALECT - سوري
    # ============================================
    {"query": "قديش في بالحمص", "expected_dish": "Hummus", "language":  "Syrian", "category": "Levantine"},
    {"query": "قديش كالوري بالتبولة", "expected_dish": "Tabbouleh", "language": "Syrian", "category": "Levantine"},
    {"query": "الشاورما قديش فيها سعرات", "expected_dish": "Shawarma", "language":  "Syrian", "category": "Levantine"},
    {"query": "الكبة النية قديش فيها", "expected_dish":  "Kibbeh", "language": "Syrian", "category":  "Levantine"},
    {"query":  "يبرق قديش كالوري", "expected_dish": "Warak Enab", "language":  "Syrian", "category": "Levantine"},
    {"query": "المجدرة قديش فيها", "expected_dish": "Mujaddara", "language":  "Syrian", "category": "Levantine"},
    
    # ============================================
    # GULF DIALECT - خليجي
    # ============================================
    {"query": "كم كالوري في المچبوس", "expected_dish": "Machboos", "language": "Gulf", "category":  "Gulf"},
    {"query": "machboos chicken calories", "expected_dish": "Machboos", "language":  "Gulf", "category": "Gulf"},
    {"query": "kabsa calories", "expected_dish": "Kabsa", "language": "Gulf", "category":  "Gulf"},
    {"query": "كم سعرة في الكبسة", "expected_dish": "Kabsa", "language":  "Gulf", "category": "Gulf"},
    {"query": "مندي دجاج كم كالوري", "expected_dish":  "Mandi", "language": "Gulf", "category":  "Gulf"},
    {"query": "mandi rice calories", "expected_dish": "Mandi", "language":  "Gulf", "category": "Gulf"},
    {"query": "هريس كم فيه سعرات", "expected_dish": "Harees", "language": "Gulf", "category":  "Gulf"},
    {"query": "harees calories", "expected_dish": "Harees", "language": "Gulf", "category":  "Gulf"},
    {"query": "ثريد كم كالوري", "expected_dish": "Thareed", "language": "Gulf", "category":  "Gulf"},
    {"query": "لقيمات كم سعرة", "expected_dish": "Luqaimat", "language":  "Gulf", "category": "Gulf"},
    
    # ============================================
    # DIFFERENT COUNTRY FOODS
    # ============================================
    # Moroccan
    {"query": "couscous calories", "expected_dish": "Couscous", "language": "English", "category": "Moroccan"},
    {"query": "الكسكس كم سعرة", "expected_dish": "Couscous", "language": "Arabic_MSA", "category": "Moroccan"},
    {"query": "tajine chicken", "expected_dish":  "Tajine", "language": "English", "category": "Moroccan"},
    {"query": "طاجين كم كالوري", "expected_dish": "Tajine", "language":  "Arabic_MSA", "category": "Moroccan"},
    {"query": "بسطيلة كم فيها سعرات", "expected_dish": "Bastilla", "language":  "Arabic_MSA", "category": "Moroccan"},
    {"query": "harira soup calories", "expected_dish": "Harira", "language":  "English", "category": "Moroccan"},
    
    # Iraqi
    {"query":  "دولمة كم سعرة", "expected_dish": "Dolma", "language":  "Arabic_MSA", "category": "Iraqi"},
    {"query":  "dolma calories", "expected_dish":  "Dolma", "language": "English", "category": "Iraqi"},
    {"query": "تشريب كم كالوري", "expected_dish": "Tashreeb", "language": "Arabic_MSA", "category": "Iraqi"},
    {"query": "مسموطة كم سعرة", "expected_dish": "Masmouta", "language": "Arabic_MSA", "category": "Iraqi"},
    
    # Palestinian
    {"query":  "مقلوبة كم كالوري", "expected_dish": "Maqluba", "language": "Arabic_MSA", "category":  "Palestinian"},
    {"query": "maqluba calories", "expected_dish": "Maqluba", "language": "English", "category": "Palestinian"},
    {"query": "ma2loube ade fiha", "expected_dish": "Maqluba", "language": "Franco", "category": "Palestinian"},
    {"query": "مسخن كم سعرة", "expected_dish": "Musakhan", "language":  "Arabic_MSA", "category": "Palestinian"},
    {"query": "musakhan calories", "expected_dish": "Musakhan", "language": "English", "category": "Palestinian"},
    
    # ============================================
    # SWEETS & DESSERTS
    # ============================================
    {"query":  "baklava calories", "expected_dish": "Baklava", "language": "English", "category": "Dessert"},
    {"query": "بقلاوة كم سعرة", "expected_dish": "Baklava", "language": "Arabic_MSA", "category": "Dessert"},
    {"query": "knafeh calories", "expected_dish": "Kunafa", "language": "English", "category":  "Dessert"},
    {"query":  "knefe ade fiha", "expected_dish":  "Kunafa", "language": "Franco", "category": "Dessert"},
    {"query": "كنافة كم كالوري", "expected_dish": "Kunafa", "language": "Arabic_MSA", "category": "Dessert"},
    {"query": "maamoul calories", "expected_dish": "Maamoul", "language": "English", "category": "Dessert"},
    {"query": "معمول كم سعرة", "expected_dish": "Maamoul", "language": "Arabic_MSA", "category":  "Dessert"},
    {"query": "قطايف كم كالوري", "expected_dish": "Qatayef", "language": "Arabic_MSA", "category":  "Dessert"},
    {"query":  "atayef calories", "expected_dish": "Qatayef", "language": "Franco", "category": "Dessert"},
    {"query": "نمورة كم سعرة", "expected_dish": "Nammoura", "language":  "Arabic_MSA", "category": "Dessert"},
    {"query": "عوامة كم كالوري", "expected_dish": "Awamat", "language": "Arabic_MSA", "category": "Dessert"},
    
    # ============================================
    # MIXED LANGUAGE QUERIES
    # ============================================
    {"query": "كم calories في hummus", "expected_dish": "Hummus", "language":  "Mixed", "category": "Levantine"},
    {"query": "shawarma كم سعرة", "expected_dish": "Shawarma", "language": "Mixed", "category": "Levantine"},
    {"query": "tabbouleh فيها كام كالوري", "expected_dish": "Tabbouleh", "language": "Mixed", "category":  "Levantine"},
    {"query":  "falafel ade calories", "expected_dish": "Falafel", "language": "Mixed", "category": "Levantine"},
    {"query": "الkibbeh كم فيها", "expected_dish":  "Kibbeh", "language": "Mixed", "category":  "Levantine"},
    
    # ============================================
    # COMPLEX QUERIES
    # ============================================
    {"query": "chicken shawarma wrap with garlic sauce", "expected_dish": "Shawarma", "language":  "English", "category": "Levantine"},
    {"query": "شاورما دجاج مع ثومية", "expected_dish": "Shawarma", "language": "Arabic_MSA", "category": "Levantine"},
    {"query": "hummus with olive oil and pine nuts", "expected_dish": "Hummus", "language":  "English", "category": "Levantine"},
    {"query": "falafel sandwich with tahini", "expected_dish": "Falafel", "language": "English", "category": "Levantine"},
    {"query": "grilled chicken tawook with rice", "expected_dish": "Tawook", "language": "English", "category": "Levantine"},
    {"query": "kibbeh nayeh raw", "expected_dish": "Kibbeh", "language":  "English", "category": "Levantine"},
    
    # ============================================
    # SINGLE INGREDIENTS (USDA Direct)
    # ============================================
    {"query": "100g rice calories", "expected_dish": "Rice", "language": "English", "category":  "Ingredient"},
    {"query": "chicken breast 150g", "expected_dish":  "Chicken", "language": "English", "category": "Ingredient"},
    {"query": "1 tablespoon olive oil", "expected_dish":  "Olive Oil", "language": "English", "category": "Ingredient"},
    {"query": "زيت زيتون ملعقة", "expected_dish": "Olive Oil", "language":  "Arabic_MSA", "category": "Ingredient"},
    {"query": "100 gram laban", "expected_dish": "Yogurt", "language":  "English", "category": "Ingredient"},
]


def query_bot(query:  str, country: str = "Lebanon") -> dict:
    """Send query to NutriArab bot."""
    try: 
        payload = {
            "message":  query,
            "country": country,
            "session_id": None
        }
        
        response = requests.post(API_URL, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            
            calories = None
            if 'totals' in data and data['totals']: 
                calories = data['totals'].get('calories')
            elif 'calories' in data:
                calories = data['calories']
            
            if calories is not None:
                calories = round(calories)
            
            return {
                'calories': calories,
                'dish_name': data.get('dish_name', ''),
                'source': data.get('source', ''),
                'status': 'success'
            }
        else: 
            return {'calories': None, 'dish_name': '', 'source': '', 'status': f'error_{response.status_code}'}
            
    except Exception as e:
        return {'calories': None, 'dish_name': '', 'source': '', 'status': f'error:  {str(e)}'}


def check_understanding(expected:  str, actual: str) -> bool:
    """Check if the bot understood the query correctly."""
    if not actual: 
        return False
    
    expected_lower = expected.lower().strip()
    actual_lower = actual.lower().strip()
    
    # Direct match or contains
    if expected_lower in actual_lower or actual_lower in expected_lower:
        return True
    
    # Common variations mapping
    variations = {
        'hummus': ['hummus', 'hommos', 'humus', '7ommos', 'حمص'],
        'tabbouleh': ['tabbouleh', 'tabboule', 'tabouli', 'tabouleh', 'تبولة'],
        'shawarma': ['shawarma', 'shawerma', 'shawrma', 'شاورما'],
        'kibbeh': ['kibbeh', 'kebbe', 'kibbe', 'كبة'],
        'falafel': ['falafel', 'flafel', 'felafil', 'فلافل', 'طعمية', 'ta3meya'],
        'warak enab': ['warak', 'grape leaves', 'stuffed leaves', 'ورق عنب', 'يبرق', 'dolma'],
        'mahashi': ['mahashi', 'محشي', 'stuffed'],
        'fattoush': ['fattoush', 'fattouche', 'فتوش'],
        'labneh': ['labneh', 'labne', 'لبنة'],
        'tawook': ['tawook', 'taouk', 'tawouk', 'طاووق'],
        'baba ghanoush': ['baba ghanoush', 'baba ghanouj', 'baba ganoush', 'متبل', 'بابا غنوج'],
        'kunafa': ['kunafa', 'knafeh', 'knefe', 'كنافة'],
        'baklava': ['baklava', 'baklawa', 'بقلاوة'],
        'koshari': ['koshari', 'koshary', 'كشري'],
        'ful medames': ['ful', 'foul', 'فول'],
        'molokhia': ['molokhia', 'molokheya', 'ملوخية'],
        'kabsa': ['kabsa', 'كبسة'],
        'mandi': ['mandi', 'مندي'],
        'couscous': ['couscous', 'كسكس'],
        'fajita': ['fajita', 'fahita'],
        'manakish': ['manakish', 'manoushe', 'مناقيش', 'مناقيش'],
        'arayes': ['arayes', '3arayess', 'عرايس'],
        'maqluba': ['maqluba', 'ma2loube', 'مقلوبة'],
        'rice': ['rice', 'رز', 'أرز'],
        'chicken': ['chicken', 'دجاج'],
        'olive oil': ['olive oil', 'زيت زيتون', 'زيت'],
        'yogurt': ['yogurt', 'laban', 'لبن', 'زبادي'],
    }
    
    for main_name, variants in variations.items():
        if expected_lower in variants or any(v in expected_lower for v in variants):
            if any(v in actual_lower for v in variants):
                return True
    
    # Check for key words
    expected_words = set(expected_lower.split())
    actual_words = set(actual_lower.split())
    common = expected_words & actual_words
    if len(common) > 0:
        return True
    
    return False


def main():
    print("=" * 70)
    print("🧠 NutriArab UNDERSTANDING EVALUATION - TEST 2")
    print("   (Multiple Languages, Dialects, Countries, Typos)")
    print("=" * 70)
    
    results = []
    total = len(TEST_CASES)
    
    # Counters
    by_language = {}
    by_category = {}
    
    print(f"\n🚀 Testing {total} queries...")
    print("-" * 70)
    
    for idx, test in enumerate(TEST_CASES):
        query = test['query']
        expected = test['expected_dish']
        language = test['language']
        category = test['category']
        
        print(f"[{idx + 1}/{total}] 🔍 {query[: 50]}...")
        
        result = query_bot(query)
        
        understood = check_understanding(expected, result['dish_name'])
        
        # Track stats by language
        if language not in by_language:
            by_language[language] = {'total':  0, 'correct': 0}
        by_language[language]['total'] += 1
        
        # Track stats by category
        if category not in by_category: 
            by_category[category] = {'total': 0, 'correct': 0}
        by_category[category]['total'] += 1
        
        if understood:
            by_language[language]['correct'] += 1
            by_category[category]['correct'] += 1
            print(f"         ✅ Understood:  '{result['dish_name']}' | {result['calories']} cal")
        else:
            print(f"         ❌ Expected: '{expected}' | Got: '{result['dish_name']}'")
        
        results.append({
            'Query': query,
            'Language': language,
            'Category': category,
            'Expected_Dish': expected,
            'Bot_DishName': result['dish_name'],
            'Bot_Calories': result['calories'],
            'Bot_Source': result['source'],
            'Understood': 'Yes' if understood else 'No',
            'Status': result['status'],
            'Date': datetime.now().strftime('%Y-%m-%d')
        })
        
        time.sleep(DELAY_SECONDS)
    
    # Save results
    df = pd.DataFrame(results)
    df.to_excel(OUTPUT_PATH, index=False)
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 UNDERSTANDING EVALUATION RESULTS")
    print("=" * 70)
    
    total_correct = sum(1 for r in results if r['Understood'] == 'Yes')
    print(f"\n   🎯 Overall Accuracy: {total_correct}/{total} ({total_correct/total*100:.1f}%)")
    
    print(f"\n   📈 By Language:")
    print(f"   {'-' * 55}")
    for lang, stats in sorted(by_language.items()):
        pct = stats['correct'] / stats['total'] * 100 if stats['total'] > 0 else 0
        bar = '█' * int(pct / 5) + '░' * (20 - int(pct / 5))
        print(f"   {lang: 20} {bar} {stats['correct']:2}/{stats['total']: 2} ({pct: 5.1f}%)")
    
    print(f"\n   📈 By Food Category:")
    print(f"   {'-' * 55}")
    for cat, stats in sorted(by_category.items()):
        pct = stats['correct'] / stats['total'] * 100 if stats['total'] > 0 else 0
        bar = '█' * int(pct / 5) + '░' * (20 - int(pct / 5))
        print(f"   {cat: 20} {bar} {stats['correct']: 2}/{stats['total']:2} ({pct:5.1f}%)")
    
    print(f"\n   📁 Results saved to: {OUTPUT_PATH}")
    print("=" * 70)


if __name__ == "__main__": 
    main()