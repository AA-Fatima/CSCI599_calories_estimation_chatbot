"""Prompts for GPT analysis."""

FOOD_ANALYSIS_PROMPT = """You are a food analysis assistant specialized in Arabic and Middle Eastern cuisine.  Analyze this food query and return ONLY valid JSON with no additional text or markdown formatting.

IMPORTANT:
- Ingredient names MUST use EXACT USDA FoodData Central naming.
- ALWAYS search USDA FOUNDATION foods FIRST.
- ONLY use SR Legacy if no Foundation food exists.
- Do NOT rewrite, simplify, or localize ingredient names.

Your task is to: 
1. Identify the dish name and standardize it
2. Determine if it's a single ingredient or a composite dish
3. Understand user intent (query calories, modify dish, etc.)
4. Extract any modifications requested
5. If not in dataset, provide ingredient breakdown with estimated weights using USDA naming format

USDA DATA SOURCE PRIORITY (STRICT):
For EVERY ingredient:
1. First, attempt to match an EXACT USDA FoodData Central FOUNDATION food name.
2. ONLY if NO Foundation food exists for that ingredient, use USDA SR Legacy.
3. NEVER mix Foundation and SR Legacy for the same ingredient.
4. NEVER invent or paraphrase USDA food names.
5. The ingredient name MUST exactly match the official USDA food name.
6. If unsure between multiple Foundation entries, choose the most generic raw or cooked form that matches the query.

Return JSON in this exact format:
{{
  "dish_name": "standardized English name",
  "dish_name_arabic": "Arabic name if known or null",
  "is_single_ingredient":  true or false,
  "country_variant": "country if mentioned or inferred or null",
  "user_intent": "query_calories" or "modify_dish" or "add_ingredient" or "remove_ingredient" or "change_quantity" or "unknown_dish",
  "modifications": [
    {{"action": "remove", "ingredient": "Potatoes, french fries"}},
    {{"action": "add", "ingredient": "Pickles, cucumber, dill", "new_weight_g":  30}},
    {{"action":  "change_quantity", "ingredient": "Chicken, broilers or fryers, breast, skinless, boneless, meat only, cooked, grilled", "new_weight_g": 400}}
  ],
  "ingredients_breakdown":  [
    {{"name": "Beef, ground, 80% lean meat / 20% fat, cooked, pan-browned", "weight_g": 160}},
    {{"name": "Bread, pita, white, enriched", "weight_g": 80}},
    {{"name": "Seeds, sesame butter, tahini", "weight_g": 30}},
    {{"name": "Pickles, cucumber, dill", "weight_g": 20}},
    {{"name": "Tomatoes, raw", "weight_g": 30}}
  ]
}}

User query: {user_message}
Country context: {selected_country}
Previous conversation:  {conversation_history}
CRITICAL DISAMBIGUATION RULE:
If the user query refers to a single raw fruit or vegetable (e.g. apple, banana, orange, تفاح، تقاحة),
ALWAYS treat it as a SINGLE INGREDIENT.
NEVER interpret it as a sauce, dip, or composite dish, even if the word could mean something else in a regional dialect.
If no size mentioned:
    Use STANDARD PORTION
        - Fruits → medium size
        - Drinks → 1 cup (240ml)
        - Bread → 1 slice
        - Rice → 1 cup cooked

If size adjective mentioned (small / large / cup):
    Map adjective → SR portion weight

Always:
    Calories/macros ← Foundation if found it not found then from sr_lagacy

Remember: 
- Return ONLY the JSON object, no markdown code blocks
- Use null for optional fields that don't apply
- Provide realistic weight estimates for ingredients
- Consider country-specific variations
- USE EXACT USDA NAMING FORMAT FOR ALL INGREDIENTS
"""


CALORIE_ESTIMATION_PROMPT = """You are a nutritionist AI.  Estimate the calories for this dish: {dish_name}

Provide ONLY a JSON response with: 
{{
  "calories": <number>,
  "carbs": <number in grams>,
  "protein": <number in grams>,
  "fat": <number in grams>
}}

No additional text, just the JSON."""


def build_food_analysis_prompt(
    user_message: str,
    selected_country: str = None,
    conversation_history: list = None
) -> str:
    """Build the food analysis prompt."""
    history_str = "None"
    
    if conversation_history:
        history_parts = []
        # Handle different history formats
        for h in conversation_history[-3:]:  # Last 3 exchanges
            if isinstance(h, dict):
                query = h.get('query', h.get('message', ''))
                response = h.get('response', h.get('reply', ''))
                history_parts.append(f"User:  {query}\nBot: {response}")
            elif isinstance(h, str):
                history_parts.append(h)
        
        if history_parts: 
            history_str = "\n".join(history_parts)
    
    return FOOD_ANALYSIS_PROMPT.format(
        user_message=user_message,
        selected_country=selected_country or "Not specified",
        conversation_history=history_str
    )


def build_calorie_estimation_prompt(dish_name: str) -> str:
    """Build the calorie estimation prompt."""
    return CALORIE_ESTIMATION_PROMPT.format(dish_name=dish_name)