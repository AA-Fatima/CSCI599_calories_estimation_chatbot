"""Refactored chat service using repositories and database."""
import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    NutritionTotals,
    IngredientWithNutrition,
    IngredientBase,
    GPTAnalysisResponse,
)
from app.ai.gpt_client import gpt_client
from app.ai.prompts import build_food_analysis_prompt
from app.repositories.dishes import DishesRepository
from app.repositories.usda import USDARepository
from app.repositories.sessions import SessionsRepository
from app.repositories.missing_dishes import MissingDishesRepository
from app.services.embedding import embedding_service
from app.services.nutrition import nutrition_service
from app.core.recipe_modifier import recipe_modifier


class ChatServiceNew:
    """Refactored chat service using repositories and async database."""
    
    async def process_message(self, request: ChatRequest, db: AsyncSession) -> ChatResponse:
        """
        Process user message and return response.
        
        Args:
            request: Chat request
            db: Database session
            
        Returns:
            Chat response
        """
        logger.info("="*60)
        logger.info("NEW CHAT REQUEST")
        logger.info("="*60)
        logger.info(f"Message: {request.message}")
        logger.info(f"Country: {request.country}")
        logger.info(f"Session ID: {request.session_id}")
        
        # Initialize repositories
        sessions_repo = SessionsRepository(db)
        dishes_repo = DishesRepository(db)
        usda_repo = USDARepository(db)
        missing_dishes_repo = MissingDishesRepository(db)
        
        # Get or create session
        if not request.session_id:
            request.session_id = str(uuid.uuid4())
            await sessions_repo.create(request.session_id, request.country)
            logger.info(f"Created new session: {request.session_id}")
        
        session = await sessions_repo.get(request.session_id)
        if not session:
            request.session_id = str(uuid.uuid4())
            session = await sessions_repo.create(request.session_id, request.country)
        
        country = request.country or session.country or 'lebanon'
        logger.info(f"Using country: {country}")
        
        # Try GPT first
        gpt_response = None
        try:
            logger.info("Attempting GPT analysis...")
            conversation_history = await sessions_repo.get_formatted_history(request.session_id, limit=3)
            prompt = build_food_analysis_prompt(
                user_message=request.message,
                selected_country=country,
                conversation_history=conversation_history
            )
            logger.debug(f"Prompt sent to GPT (first 200 chars): {prompt[:200]}...")
            gpt_response = gpt_client.analyze_food_query(prompt)
            
            if gpt_response:
                logger.info("GPT Response received:")
                logger.info(f"  - Dish name: {gpt_response.dish_name}")
                logger.info(f"  - Arabic name: {gpt_response.dish_name_arabic}")
                logger.info(f"  - Is single ingredient: {gpt_response.is_single_ingredient}")
                logger.info(f"  - User intent: {gpt_response.user_intent}")
            else:
                logger.warning("GPT returned None (no API key or API error)")
                
        except Exception as e:
            logger.error(f"GPT error: {e}")
        
        # If GPT fails, try direct database search
        if not gpt_response:
            logger.info("FALLBACK MODE: Searching database directly...")
            return await self._fallback_search(
                request.session_id,
                request.message,
                country,
                dishes_repo,
                usda_repo,
                sessions_repo
            )
        
        # Process based on whether it's a single ingredient or dish
        if gpt_response.is_single_ingredient:
            logger.info("Processing as SINGLE INGREDIENT...")
            return await self._process_single_ingredient(
                request.session_id,
                gpt_response,
                usda_repo,
                sessions_repo
            )
        else:
            logger.info("Processing as COMPLETE DISH...")
            return await self._process_dish(
                request.session_id,
                country,
                gpt_response,
                dishes_repo,
                usda_repo,
                sessions_repo,
                missing_dishes_repo
            )
    
    async def _fallback_search(
        self,
        session_id: str,
        message: str,
        country: str,
        dishes_repo: DishesRepository,
        usda_repo: USDARepository,
        sessions_repo: SessionsRepository
    ) -> ChatResponse:
        """Fallback when GPT is unavailable - search directly in database."""
        logger.info("-"*40)
        logger.info("FALLBACK SEARCH")
        logger.info("-"*40)
        
        # Clean up the message
        dish_name = message.strip().lower()
        patterns_to_remove = [
            "calories in ", "calorie in ", "cal in ",
            "how many calories in ", "what are the calories in ",
        ]
        
        for pattern in patterns_to_remove:
            dish_name = dish_name.replace(pattern, "")
        
        dish_name = dish_name.strip()
        logger.info(f"Cleaned dish name: '{dish_name}'")
        
        # Generate embedding for search
        query_embedding = embedding_service.encode(dish_name)
        
        # Search in dishes database with country priority
        logger.info(f"Searching dishes database for '{dish_name}' in {country}...")
        result = await dishes_repo.search_with_country_priority(
            query_embedding,
            country,
            threshold=0.7  # Lower threshold for fallback
        )
        
        if result:
            dish, similarity, is_from_user_country = result
            logger.info(f"FOUND in dishes database! (similarity: {similarity:.3f})")
            
            # Parse ingredients
            ingredients = self._parse_dish_ingredients(dish.ingredients)
            totals = nutrition_service.calculate_totals(ingredients)
            
            message_text = f"{dish.dish_name} contains {totals.calories:.0f} calories."
            if not is_from_user_country:
                message_text += f" (This is a {dish.country} dish.)"
            
            await sessions_repo.update(
                session_id,
                last_dish=dish.dish_name,
                last_dish_ingredients=[ing.dict() for ing in ingredients]
            )
            
            return ChatResponse(
                session_id=session_id,
                dish_name=dish.dish_name,
                dish_name_arabic=dish.dish_name_arabic,
                ingredients=ingredients,
                totals=totals,
                source="dataset",
                message=message_text
            )
        
        logger.info("NOT FOUND in dishes database")
        
        # Try as single ingredient in USDA
        logger.info(f"Trying USDA search for '{dish_name}'...")
        usda_result = await usda_repo.search(query_embedding, threshold=0.7)
        
        if usda_result:
            food, similarity = usda_result
            logger.info(f"FOUND in USDA! (similarity: {similarity:.3f})")
            
            # Create ingredient (default 100g)
            ingredient = IngredientWithNutrition(
                name=food.description,
                weight_g=100.0,
                usda_fdc_id=food.fdc_id,
                calories=food.calories,
                carbs=food.carbs,
                protein=food.protein,
                fat=food.fat
            )
            
            totals = nutrition_service.calculate_totals([ingredient])
            message_text = f"{food.description} (100g) contains {totals.calories:.0f} calories."
            
            return ChatResponse(
                session_id=session_id,
                dish_name=food.description,
                dish_name_arabic=None,
                ingredients=[ingredient],
                totals=totals,
                source="dataset",
                message=message_text
            )
        
        logger.info("NOT FOUND in USDA either")
        
        # Nothing found
        return self._create_error_response(
            session_id,
            f"Sorry, I couldn't find '{dish_name}' in my database. "
            f"Please try a different dish name or check the spelling."
        )
    
    async def _process_single_ingredient(
        self,
        session_id: str,
        gpt_response: GPTAnalysisResponse,
        usda_repo: USDARepository,
        sessions_repo: SessionsRepository
    ) -> ChatResponse:
        """Process query for a single ingredient."""
        logger.info("-"*40)
        logger.info("SINGLE INGREDIENT PROCESSING")
        logger.info("-"*40)
        
        if not gpt_response.ingredients_breakdown:
            logger.error("No ingredients in GPT breakdown")
            return self._create_error_response(
                session_id,
                "Could not identify the ingredient."
            )
        
        ingredient_base = gpt_response.ingredients_breakdown[0]
        logger.info(f"Searching for: {ingredient_base.name} ({ingredient_base.weight_g}g)")
        
        # Generate embedding and search
        query_embedding = embedding_service.encode(ingredient_base.name)
        result = await usda_repo.search(query_embedding)
        
        if not result:
            logger.error(f"Could not find in USDA: {ingredient_base.name}")
            return self._create_error_response(
                session_id,
                f"Could not find nutritional data for {ingredient_base.name}."
            )
        
        food, similarity = result
        logger.info(f"Found: {food.description} (similarity: {similarity:.3f})")
        
        # Calculate nutrition for requested weight
        nutrition = nutrition_service.calculate_nutrition_by_weight(
            food.calories,
            food.carbs,
            food.protein,
            food.fat,
            ingredient_base.weight_g
        )
        
        ingredient = IngredientWithNutrition(
            name=food.description,
            weight_g=ingredient_base.weight_g,
            usda_fdc_id=food.fdc_id,
            calories=nutrition['calories'],
            carbs=nutrition['carbs'],
            protein=nutrition['protein'],
            fat=nutrition['fat']
        )
        
        totals = nutrition_service.calculate_totals([ingredient])
        message_text = f"{ingredient.name} ({ingredient.weight_g}g) contains {totals.calories:.0f} calories."
        
        await sessions_repo.add_to_history(session_id, gpt_response.dish_name, message_text)
        
        return ChatResponse(
            session_id=session_id,
            dish_name=ingredient.name,
            dish_name_arabic=gpt_response.dish_name_arabic,
            ingredients=[ingredient],
            totals=totals,
            source="dataset",
            message=message_text
        )
    
    async def _process_dish(
        self,
        session_id: str,
        country: str,
        gpt_response: GPTAnalysisResponse,
        dishes_repo: DishesRepository,
        usda_repo: USDARepository,
        sessions_repo: SessionsRepository,
        missing_dishes_repo: MissingDishesRepository
    ) -> ChatResponse:
        """Process query for a complete dish."""
        logger.info("-"*40)
        logger.info("DISH PROCESSING")
        logger.info("-"*40)
        logger.info(f"Dish name from GPT: {gpt_response.dish_name}")
        logger.info(f"Country: {country}")
        
        # Search for dish in database with country priority
        query_embedding = embedding_service.encode(gpt_response.dish_name)
        result = await dishes_repo.search_with_country_priority(
            query_embedding,
            country,
            threshold=0.85
        )
        
        if result:
            dish, similarity, is_from_user_country = result
            logger.info(f"FOUND in dishes database! (similarity: {similarity:.3f})")
            
            # Parse ingredients from database
            ingredients = self._parse_dish_ingredients(dish.ingredients)
            source = "dataset"
            actual_dish_name = dish.dish_name
            
            logger.info(f"Ingredients from database:")
            for ing in ingredients:
                logger.info(f"  • {ing.name}: {ing.weight_g}g = {ing.calories} cal")
        else:
            logger.info("NOT in dishes database - using GPT breakdown")
            
            # Dish not in dataset - use GPT's breakdown
            if not gpt_response.ingredients_breakdown:
                logger.error("GPT provided no ingredients breakdown")
                return self._create_error_response(
                    session_id,
                    f"Sorry, I don't have information about {gpt_response.dish_name}."
                )
            
            logger.info("Searching USDA for each GPT ingredient:")
            
            # Calculate nutrition for each ingredient
            ingredients = []
            for ing_base in gpt_response.ingredients_breakdown:
                logger.info(f"  Searching: {ing_base.name} ({ing_base.weight_g}g)...")
                
                # Generate embedding and search
                ing_embedding = embedding_service.encode(ing_base.name)
                ing_result = await usda_repo.search(ing_embedding)
                
                if ing_result:
                    food, similarity = ing_result
                    logger.info(f"    ✓ Found: {food.description} (similarity: {similarity:.3f})")
                    
                    # Calculate nutrition for weight
                    nutrition = nutrition_service.calculate_nutrition_by_weight(
                        food.calories,
                        food.carbs,
                        food.protein,
                        food.fat,
                        ing_base.weight_g
                    )
                    
                    ingredient = IngredientWithNutrition(
                        name=food.description,
                        weight_g=ing_base.weight_g,
                        usda_fdc_id=food.fdc_id,
                        calories=nutrition['calories'],
                        carbs=nutrition['carbs'],
                        protein=nutrition['protein'],
                        fat=nutrition['fat']
                    )
                    ingredients.append(ingredient)
                else:
                    logger.warning(f"    ✗ Not found, skipping")
            
            source = "ai_estimated"
            actual_dish_name = gpt_response.dish_name
            
            # Log as missing dish
            try:
                await missing_dishes_repo.add_or_update(
                    dish_name=gpt_response.dish_name,
                    dish_name_arabic=gpt_response.dish_name_arabic,
                    country=country,
                    query_text=gpt_response.dish_name,
                    gpt_response=gpt_response.model_dump() if hasattr(gpt_response, 'model_dump') else gpt_response.dict(),
                    ingredients=[
                        {'name': ing.name, 'weight_g': ing.weight_g}
                        for ing in gpt_response.ingredients_breakdown
                    ]
                )
                logger.info("Logged as missing dish for admin review")
            except Exception as e:
                logger.error(f"Error logging missing dish: {e}")
        
        # Apply modifications if any
        if gpt_response.modifications:
            logger.info(f"Applying {len(gpt_response.modifications)} modifications...")
            for mod in gpt_response.modifications:
                logger.info(f"  - {mod.action}: {mod.ingredient}")
            ingredients = recipe_modifier.apply_modifications(
                ingredients,
                gpt_response.modifications
            )
        
        # Calculate totals
        totals = nutrition_service.calculate_totals(ingredients)
        logger.info("FINAL TOTALS:")
        logger.info(f"  - Calories: {totals.calories}")
        logger.info(f"  - Carbs: {totals.carbs}g")
        logger.info(f"  - Protein: {totals.protein}g")
        logger.info(f"  - Fat: {totals.fat}g")
        logger.info(f"  - Source: {source}")
        
        # Build message
        source_note = " (estimated)" if source == "ai_estimated" else ""
        message_text = f"{actual_dish_name} contains {totals.calories:.0f} calories{source_note}."
        
        # Update session
        await sessions_repo.update(
            session_id,
            last_dish=actual_dish_name,
            last_dish_ingredients=[ing.dict() for ing in ingredients]
        )
        await sessions_repo.add_to_history(session_id, actual_dish_name, message_text)
        
        logger.info("="*60)
        logger.info(f"RESPONSE: {message_text}")
        logger.info("="*60)
        
        return ChatResponse(
            session_id=session_id,
            dish_name=actual_dish_name,
            dish_name_arabic=gpt_response.dish_name_arabic,
            ingredients=ingredients,
            totals=totals,
            source=source,
            message=message_text
        )
    
    def _parse_dish_ingredients(self, ingredients_json: List[dict]) -> List[IngredientWithNutrition]:
        """Parse ingredients from database JSON."""
        ingredients = []
        for ing in ingredients_json:
            ingredient = IngredientWithNutrition(
                name=ing['name'],
                weight_g=float(ing['weight_g']),
                usda_fdc_id=ing.get('usda_fdc_id'),
                calories=float(ing.get('calories', 0)),
                carbs=float(ing.get('carbs', 0)),
                protein=float(ing.get('protein', 0)),
                fat=float(ing.get('fat', 0))
            )
            ingredients.append(ingredient)
        return ingredients
    
    def _create_error_response(
        self,
        session_id: str,
        message: str
    ) -> ChatResponse:
        """Create an error response."""
        logger.error(f"ERROR RESPONSE: {message}")
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
chat_service_new = ChatServiceNew()
