"""Chat service - main orchestration logic."""
from typing import Optional, List
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    NutritionTotals,
    IngredientWithNutrition,
    IngredientBase,
    GPTAnalysisResponse,
    ModificationAction
)
from app.ai.gpt_client import gpt_client
from app.ai.prompts import build_food_analysis_prompt
from app.data.dishes_handler import dishes_handler
from app.core.ingredient_manager import ingredient_manager
from app.core.recipe_modifier import recipe_modifier
from app.core.calorie_calculator import calorie_calculator
from app.services.session_manager import session_manager
from app.services.missing_dish_service import missing_dish_service


class ChatService: 
    """Main chat service orchestrating the entire flow."""
    
    def process_message(self, request: ChatRequest) -> ChatResponse:
        """
        Process user message and return response.
        """
        print("\n" + "="*60)
        print("🔵 NEW CHAT REQUEST")
        print("="*60)
        print(f"📝 Message: {request.message}")
        print(f"🌍 Country: {request.country}")
        print(f"🔑 Session ID: {request.session_id}")
        
        # Get or create session
        if not request.session_id:
            request.session_id = session_manager.create_session(request.country)
            print(f"✨ Created new session:  {request.session_id}")
        
        session = session_manager.get_session(request.session_id)
        if not session:
            request.session_id = session_manager.create_session(request.country)
            session = session_manager.get_session(request.session_id)
        
        country = request.country or session.get('country', 'lebanon')
        print(f"🌍 Using country: {country}")
        
        # Try GPT first
        gpt_response = None
        try:
            print("\n📡 Attempting GPT analysis...")
            conversation_history = session_manager.get_conversation_history(request.session_id)
            prompt = build_food_analysis_prompt(
                user_message=request.message,
                selected_country=country,
                conversation_history=conversation_history
            )
            print(f"📋 Prompt sent to GPT (first 200 chars): {prompt[:200]}...")
            gpt_response = gpt_client.analyze_food_query(prompt)
            
            if gpt_response:
                print("\n✅ GPT Response received:")
                print(f"   - Dish name: {gpt_response.dish_name}")
                print(f"   - Arabic name: {gpt_response.dish_name_arabic}")
                print(f"   - Is single ingredient: {gpt_response.is_single_ingredient}")
                print(f"   - User intent: {gpt_response.user_intent}")
                print(f"   - Modifications:  {gpt_response.modifications}")
                print(f"   - Ingredients breakdown: {len(gpt_response.ingredients_breakdown)} items")
                for i, ing in enumerate(gpt_response.ingredients_breakdown):
                    print(f"      {i+1}.{ing.name} - {ing.weight_g}g")
            else:
                print("❌ GPT returned None (no API key or API error)")
                
        except Exception as e:
            print(f"❌ GPT error: {e}")
        
        # If GPT fails, try direct database search (FALLBACK MODE)
        if not gpt_response: 
            print("\n🔄 FALLBACK MODE:  Searching database directly...")
            return self._fallback_search(request.session_id, request.message, country)
        
        # Process based on whether it's a single ingredient or dish
        if gpt_response.is_single_ingredient: 
            print("\n🥕 Processing as SINGLE INGREDIENT...")
            return self._process_single_ingredient(request.session_id, gpt_response)
        else: 
            print("\n🍽️ Processing as COMPLETE DISH...")
            return self._process_dish(request.session_id, country, gpt_response)
    
    def _fallback_search(
        self,
        session_id: str,
        message: str,
        country: str
    ) -> ChatResponse:
        """
        Fallback when GPT is unavailable - search directly in database.
        """
        print("\n" + "-"*40)
        print("🔍 FALLBACK SEARCH")
        print("-"*40)
        
        # Clean up the message to get dish name
        dish_name = message.strip().lower()
        print(f"📝 Original message: {message}")
        
        # Common patterns to remove
        patterns_to_remove = [
            "calories in ", "calorie in ", "cal in ",
            "how many calories in ", "what are the calories in ",
            "كم سعرة في ", "سعرات ", "كم كالوري في ",
            "kam calorie ", "kam cal ", "calories ", "calorie "
        ]
        
        for pattern in patterns_to_remove:
            if pattern in dish_name: 
                print(f"   Removing pattern: '{pattern}'")
            dish_name = dish_name.replace(pattern, "")
        
        dish_name = dish_name.strip()
        print(f"🔎 Cleaned dish name: '{dish_name}'")
        
        # Search in dishes database
        print(f"\n📊 Searching dishes database for '{dish_name}' in {country}...")
        dish = dishes_handler.find_dish(dish_name, country)
        
        if dish:
            print(f"✅ FOUND in dishes database!")
            print(f"   - Dish:  {dish}")
            
            ingredients = dishes_handler.get_dish_ingredients(dish)
            print(f"   - Ingredients count: {len(ingredients)}")
            for ing in ingredients:
                print(f"      • {ing.name}:  {ing.weight_g}g = {ing.calories} cal")
            
            totals = calorie_calculator.calculate_totals(ingredients)
            print(f"   - Total calories: {totals.calories}")
            
            actual_dish_name = dish.get('dish name', dish.get('dish_name', dish_name))
            
            message = f"{actual_dish_name} contains {totals.calories:.0f} calories."
            
            session_manager.update_session(
                session_id,
                last_dish=actual_dish_name,
                last_dish_ingredients=ingredients
            )
            
            return ChatResponse(
                session_id=session_id,
                dish_name=actual_dish_name,
                dish_name_arabic=None,
                ingredients=ingredients,
                totals=totals,
                source="dataset",
                message=message
            )
        
        print(f"❌ NOT FOUND in dishes database")
        
        # Try as single ingredient in USDA
        print(f"\n🥬 Trying USDA search for '{dish_name}'...")
        ingredient_base = IngredientBase(name=dish_name, weight_g=100.0)
        ingredient = ingredient_manager.search_and_calculate(ingredient_base)
        
        if ingredient:
            print(f"✅ FOUND in USDA!")
            print(f"   - Matched:  {ingredient.name}")
            print(f"   - Calories per 100g: {ingredient.calories}")
            
            totals = calorie_calculator.calculate_totals([ingredient])
            message = f"{ingredient.name} (100g) contains {totals.calories:.0f} calories."
            
            return ChatResponse(
                session_id=session_id,
                dish_name=ingredient.name,
                dish_name_arabic=None,
                ingredients=[ingredient],
                totals=totals,
                source="dataset",
                message=message
            )
        
        print(f"❌ NOT FOUND in USDA either")
        
        # Nothing found
        return self._create_error_response(
            session_id,
            f"Sorry, I couldn't find '{dish_name}' in my database."
            f"Please try a different dish name or check the spelling."
        )
    
    def _process_single_ingredient(
        self,
        session_id: str,
        gpt_response:  GPTAnalysisResponse
    ) -> ChatResponse:
        """Process query for a single ingredient."""
        print("\n" + "-"*40)
        print("🥕 SINGLE INGREDIENT PROCESSING")
        print("-"*40)
        
        if not gpt_response.ingredients_breakdown:
            print("❌ No ingredients in GPT breakdown")
            return self._create_error_response(
                session_id,
                "Could not identify the ingredient."
            )
        
        ingredient_base = gpt_response.ingredients_breakdown[0]
        print(f"📝 Searching for: {ingredient_base.name} ({ingredient_base.weight_g}g)")
        
        ingredient = ingredient_manager.search_and_calculate(ingredient_base)
        
        if not ingredient:
            print(f"❌ Could not find in USDA:  {ingredient_base.name}")
            return self._create_error_response(
                session_id,
                f"Could not find nutritional data for {ingredient_base.name}."
            )
        
        print(f"✅ Found:  {ingredient.name}")
        print(f"   - Calories:  {ingredient.calories}")
        print(f"   - Carbs: {ingredient.carbs}g")
        print(f"   - Protein: {ingredient.protein}g")
        print(f"   - Fat: {ingredient.fat}g")
        
        totals = calorie_calculator.calculate_totals([ingredient])
        
        message = f"{ingredient.name} ({ingredient.weight_g}g) contains {totals.calories:.0f} calories."
        
        session_manager.add_to_history(session_id, gpt_response.dish_name, message)
        
        return ChatResponse(
            session_id=session_id,
            dish_name=ingredient.name,
            dish_name_arabic=gpt_response.dish_name_arabic,
            ingredients=[ingredient],
            totals=totals,
            source="dataset",
            message=message
        )
    
    def _process_dish(
        self,
        session_id:  str,
        country: Optional[str],
        gpt_response:  GPTAnalysisResponse
    ) -> ChatResponse:
        """Process query for a complete dish."""
        print("\n" + "-"*40)
        print("🍽️ DISH PROCESSING")
        print("-"*40)
        print(f"📝 Dish name from GPT: {gpt_response.dish_name}")
        print(f"🌍 Country:  {country}")
        
        # First, check if dish exists in dataset
        print(f"\n📊 Searching dishes database...")
        dish = dishes_handler.find_dish(gpt_response.dish_name, country)
        
        if dish: 
            print(f"✅ FOUND in dishes database!")
            print(f"   - Dish data: {dish}")
            
            ingredients = dishes_handler.get_dish_ingredients(dish)
            source = "dataset"
            actual_dish_name = dish.get('dish name', dish.get('dish_name', gpt_response.dish_name))
            
            print(f"   - Ingredients from database:")
            for ing in ingredients:
                print(f"      • {ing.name}:  {ing.weight_g}g = {ing.calories} cal")
        else:
            print(f"❌ NOT in dishes database - using GPT breakdown")
            
            # Dish not in dataset - use GPT's breakdown
            if not gpt_response.ingredients_breakdown:
                print("❌ GPT provided no ingredients breakdown")
                return self._create_error_response(
                    session_id,
                    f"Sorry, I don't have information about {gpt_response.dish_name}."
                )
            
            print(f"\n🔍 Searching USDA for each GPT ingredient:")
            
            # Calculate nutrition for each ingredient
            ingredients = []
            for ing_base in gpt_response.ingredients_breakdown:
                print(f"   Searching:  {ing_base.name} ({ing_base.weight_g}g)...")
                ing = ingredient_manager.search_and_calculate(ing_base)
                if ing: 
                    print(f"      ✅ Found:  {ing.name} = {ing.calories} cal")
                    ingredients.append(ing)
                else:
                    print(f"      ❌ Not found, skipping")
            
            source = "ai_estimated"
            actual_dish_name = gpt_response.dish_name
            
            # Log as missing dish
            try:
                missing_dish_service.add_missing_dish(
                    dish_name=gpt_response.dish_name,
                    dish_name_arabic=gpt_response.dish_name_arabic,
                    country=country or "Unknown",
                    query_text=gpt_response.dish_name,
                    gpt_response=gpt_response.model_dump() if hasattr(gpt_response, 'model_dump') else gpt_response.dict(),
                    ingredients=gpt_response.ingredients_breakdown
                )
                print(f"📝 Logged as missing dish for admin review")
            except Exception as e: 
                print(f"⚠️ Error logging missing dish: {e}")
        
        # Apply modifications if any
        if gpt_response.modifications:
            print(f"\n🔧 Applying {len(gpt_response.modifications)} modifications...")
            for mod in gpt_response.modifications:
                print(f"   - {mod.action}: {mod.ingredient}")
            ingredients = recipe_modifier.apply_modifications(
                ingredients,
                gpt_response.modifications
            )
        
        # Calculate totals
        totals = calorie_calculator.calculate_totals(ingredients)
        print(f"\n📊 FINAL TOTALS:")
        print(f"   - Calories:  {totals.calories}")
        print(f"   - Carbs: {totals.carbs}g")
        print(f"   - Protein: {totals.protein}g")
        print(f"   - Fat: {totals.fat}g")
        print(f"   - Source: {source}")
        
        # Build message
        source_note = " (estimated)" if source == "ai_estimated" else ""
        message = f"{actual_dish_name} contains {totals.calories:.0f} calories{source_note}."
        
        # Update session
        session_manager.update_session(
            session_id,
            last_dish=actual_dish_name,
            last_dish_ingredients=ingredients
        )
        session_manager.add_to_history(session_id, actual_dish_name, message)
        
        print("\n" + "="*60)
        print(f"✅ RESPONSE:  {message}")
        print("="*60 + "\n")
        
        return ChatResponse(
            session_id=session_id,
            dish_name=actual_dish_name,
            dish_name_arabic=gpt_response.dish_name_arabic,
            ingredients=ingredients,
            totals=totals,
            source=source,
            message=message
        )
    
    def _create_error_response(
        self,
        session_id: str,
        message: str
    ) -> ChatResponse:
        """Create an error response."""
        print(f"\n❌ ERROR RESPONSE:  {message}\n")
        return ChatResponse(
            session_id=session_id,
            dish_name="Error",
            dish_name_arabic=None,
            ingredients=[],
            totals=NutritionTotals(calories=0, carbs=0, protein=0, fat=0),
            source="dataset",
            message=message
        )


# Global instance
chat_service = ChatService()