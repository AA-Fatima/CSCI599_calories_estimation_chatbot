import requests
import pandas as pd
from datetime import datetime
import time

# ============================================
# CONFIGURATION - USE LOCAL! 
# ============================================
API_URL = "http://localhost:8000/api/chat"  # LOCAL SERVER! 
INPUT_FILE = "evaluation_accuracy.xlsx"
OUTPUT_FILE = "evaluation_results.xlsx"

# ============================================
# LOAD DATA
# ============================================
print("Loading dataset...")
df = pd.read_excel(INPUT_FILE)

print(f"Found {len(df)} items to evaluate")
print("-" * 50)

# ============================================
# QUERY CHATBOT FOR EACH ITEM
# ============================================
chatbot_dish_names = []
chatbot_calories = []
chatbot_dates = []

today = datetime.now().strftime("%A, %B %d, %Y")

for index, row in df.iterrows():
    query = row['Description_English']
    
    try:
        response = requests.post(
            API_URL, 
            json={"message": query},
            timeout=60
        )
        data = response.json()
        
        # Extract values
        dish_name = data.get('dish_name')
        totals = data.get('totals', {})
        calories = totals.get('calories')
        
        # Round calories
        if calories is not None:
            calories = round(calories)
        
        chatbot_dish_names.append(dish_name)
        chatbot_calories.append(calories)
        chatbot_dates.append(today)
        
        print(f"✅ {index+1}/{len(df)}: {query[:40]:<40} → {calories} cal")
        
    except Exception as e:
        chatbot_dish_names.append(None)
        chatbot_calories.append(None)
        chatbot_dates.append(today)
        print(f"❌ {index+1}/{len(df)}: {query[:40]:<40} → ERROR: {e}")
    
    time.sleep(0.5)

# ============================================
# SAVE RESULTS
# ============================================
df['chatbot_dish_name'] = chatbot_dish_names
df['chatbot_calories'] = chatbot_calories
df['chatbot_date'] = chatbot_dates

df.to_excel(OUTPUT_FILE, index=False)

print("-" * 50)
print(f"✅ Done!  Saved to {OUTPUT_FILE}")
print(f"✅ Success: {len([c for c in chatbot_calories if c is not None])}/{len(df)}")
print(f"❌ Errors:  {len([c for c in chatbot_calories if c is None])}/{len(df)}")