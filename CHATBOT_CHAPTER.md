# Chatbot Phase: AI-Powered Arabic Food Calorie Estimation System

## Overview

This phase implements an intelligent conversational chatbot system designed to estimate calories and nutritional information for Arabic and Middle Eastern cuisine. The chatbot uses natural language processing (NLP) and semantic search to understand user queries in conversational Arabic or English and provide accurate calorie estimations.

## Key Technologies

### Artificial Intelligence & Natural Language Processing
- **OpenAI GPT-4o**: Utilized for intent detection, dish name standardization, and ingredient breakdown from natural language queries
- **Sentence Transformers**: Employs the `all-MiniLM-L6-v2` model to generate 384-dimensional embeddings for semantic similarity matching

### Vector Search & Semantic Matching
- **PostgreSQL with pgvector**: Implements vector similarity search using cosine distance to find dishes and ingredients based on meaning rather than exact text matching
- **Multi-phase search strategy**: Combines exact matching, prefix matching, and vector similarity search with confidence thresholds to ensure accurate results
- **Country-aware prioritization**: Search results prioritize dishes from the user's specified country while maintaining global fallback options

### Database Architecture
- **PostgreSQL**: Primary database storing dishes, USDA food data, conversation sessions, and missing dish tracking
- **Repository Pattern**: Clean separation of data access logic from business logic
- **Asynchronous Operations**: Full async/await implementation for optimal performance

## Core Functionalities

### 1. Natural Language Understanding
The system processes user queries in conversational format, supporting:
- Calorie queries (e.g., "How many calories in shawarma?")
- Modifications (e.g., "shawarma without potatoes")
- Single ingredient queries
- Multi-ingredient dish inquiries

### 2. Intelligent Dish Matching
- **Semantic Search**: Uses vector embeddings to match dish variations (e.g., "shawarma", "shawerma", "شاورما")
- **Exact/Prefix Matching**: Prioritizes direct text matches before semantic search for higher accuracy
- **Partial Match Filtering**: Prevents overly broad matches (e.g., "shawarma" matching "shawarma pizza") through intelligent filtering
- **Progressive Threshold Adjustment**: Dynamically adjusts similarity thresholds to balance recall and precision

### 3. Ingredient Management
- **USDA Food Database Integration**: Comprehensive nutritional data from USDA FoodData Central
- **Smart Ingredient Matching**: Handles variations like "potatoes" matching "Potatoes, french fried..." and "tomato" matching both "Tomatoes, grape" and "Tomatoes, roma"
- **Ingredient Modifications**: Supports adding, removing, and changing quantities of ingredients in real-time
- **Automatic Nutrition Calculation**: Calculates total calories, carbohydrates, protein, and fat from ingredient breakdowns

### 4. Session & Context Management
- **Persistent Conversations**: Maintains conversation history for contextual understanding
- **Session Tracking**: Stores user sessions with country preferences and last accessed dishes
- **Contextual Responses**: Uses conversation history to provide more accurate and relevant responses

### 5. Missing Dish Tracking
- **Automatic Logging**: Records dishes not found in the database for administrative review
- **Query Frequency Tracking**: Tracks how often users request missing dishes
- **Admin Dashboard Integration**: Provides interface for reviewing and adding missing dishes to the database

## Architecture Highlights

### Backend Structure
- **FastAPI Framework**: RESTful API with automatic OpenAPI documentation
- **Service Layer**: Chat service orchestrates GPT analysis, database searches, and response generation
- **Repository Layer**: Dedicated repositories for dishes, USDA foods, sessions, and missing dishes
- **Configuration Management**: Centralized settings with environment variable support

### Search Strategy
1. **Phase 0**: Exact or prefix text matching (highest accuracy)
2. **Phase 1**: Vector similarity search within user's country
3. **Phase 2**: Global vector similarity search with lower threshold
4. **Fallback**: GPT-based ingredient breakdown if no confident match found

### Quality Assurance
- **Confidence Thresholds**: Configurable similarity thresholds (default 0.75) ensure high-quality matches
- **Minimum Confidence Levels**: Additional `min_confidence` parameter (0.70) filters out marginal matches
- **Explicit Fallback Logic**: Forces GPT breakdown for low-confidence matches (<0.70 similarity)

## Admin Dashboard

A comprehensive administrative interface enables:
- **Dish Management**: Create, read, update, and delete dishes
- **Missing Dish Review**: Review, approve, and add missing dishes to the database
- **Statistics**: View total dishes, missing dish counts, and country distributions
- **USDA Search**: Search and validate ingredients in the USDA database

## Performance Optimizations

- **Vector Indexing**: IVFFlat indexes on embeddings for fast similarity search
- **Lazy Loading**: Embedding model loaded on first use
- **Database Connection Pooling**: Efficient connection management
- **Caching**: Conversation history and search results cached appropriately

## Conclusion

This chatbot phase successfully combines modern AI technologies with robust database architecture to provide accurate, context-aware calorie estimation for Arabic and Middle Eastern cuisine. The semantic search capabilities ensure the system handles various dish name spellings and variations, while the intelligent matching logic prevents false positives. The system is production-ready with comprehensive error handling, logging, and administrative tools.
