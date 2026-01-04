# Arabic Food Calorie Estimation Chatbot

Master's Thesis Project - Calorie estimation for Arabic/Middle Eastern cuisine using AI-powered natural language understanding.

## Overview

This project implements an AI-powered chatbot system that calculates calories and provides nutritional information for Arabic and Middle Eastern dishes. It uses ChatGPT/DeepSeek APIs for natural language understanding while relying on local USDA datasets for accurate calorie calculations.

## Tech Stack

- **Frontend**: Angular 17+ (TypeScript, SCSS)
- **Backend**: Python FastAPI
- **AI Integration**: OpenAI GPT-4 / DeepSeek API
- **Data**: USDA Foundation JSON, USDA SR Legacy JSON, Custom Arabic dishes Excel

## Features

### 1. Landing Page
- Country selection dropdown (15+ Arab countries)
- Beautiful UI with Arabic food imagery/colors
- Supports country-specific dish variants

### 2. Chatbot Interface
- Multi-turn conversations
- Support for Arabic, English, and Arabizi
- Real-time calorie calculations
- Detailed nutritional breakdown (Calories, Carbs, Protein, Fats)
- Ingredient-by-ingredient breakdown table
- Modification support (add/remove/change ingredients)

### 3. Admin Panel
- Dashboard with statistics
- View and manage missing dishes
- Add/edit/delete dishes
- Link ingredients to USDA database

### 4. Comparison/Evaluation
- Compare accuracy with ChatGPT and DeepSeek
- Calculate MAE, RMSE, MAPE metrics
- Generate detailed comparison reports

## Quick Start

### Prerequisites
- Docker and Docker Compose
- OpenAI API key (optional, for full functionality)
- DeepSeek API key (optional, for comparison)

### Using Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/AA-Fatima/599_chatbot_calories_estimation.git
cd 599_chatbot_calories_estimation
git checkout powered-by-ai
```

2. Create a `.env` file in the backend directory:
```bash
cp backend/.env.example backend/.env
```

3. Add your API keys to `backend/.env`:
```
OPENAI_API_KEY=your_openai_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

4. Start the application:
```bash
docker-compose up --build
```

5. Access the application:
- Frontend: http://localhost:4200
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Manual Setup

#### Backend

1. Navigate to backend directory:
```bash
cd backend
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file and add API keys:
```bash
cp .env.example .env
# Edit .env with your API keys
```

5. Run the backend:
```bash
uvicorn app.main:app --reload
```

#### Frontend

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Run the development server:
```bash
ng serve
```

4. Access the application at http://localhost:4200

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/routes/         # API endpoints
│   │   ├── ai/                 # GPT & DeepSeek clients
│   │   ├── core/               # Core calculation logic
│   │   ├── data/               # Data handlers
│   │   ├── models/             # Pydantic schemas
│   │   ├── services/           # Business logic
│   │   ├── evaluation/         # Comparison module
│   │   └── main.py             # FastAPI app
│   ├── data/                   # Datasets
│   │   ├── USDA_foundation.json
│   │   ├── USDA_sr_legacy.json
│   │   ├── dishes.xlsx
│   │   └── test_queries.xlsx
│   └── Dockerfile
├── frontend/
│   ├── src/app/
│   │   ├── components/         # Angular components
│   │   ├── models/             # TypeScript interfaces
│   │   └── services/           # API services
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## API Endpoints

### Chat
- `POST /api/chat` - Send message to chatbot
- `GET /api/chat/history/{session_id}` - Get conversation history

### Admin
- `GET /api/admin/stats` - Get dashboard statistics
- `GET /api/admin/missing-dishes` - List missing dishes
- `GET /api/admin/dishes` - List all dishes
- `POST /api/admin/dishes` - Create new dish
- `PUT /api/admin/dishes/{id}` - Update dish
- `DELETE /api/admin/dishes/{id}` - Delete dish

### Countries
- `GET /api/countries` - Get list of available countries

### Comparison
- `POST /api/comparison/run` - Run evaluation comparison
- `GET /api/comparison/test-queries` - Get test queries

## Sample Queries

The chatbot understands various query formats:

- **Arabic**: "كم سعرة في الشاورما"
- **English**: "how many calories in shawarma"
- **Arabizi**: "kam calorie bl kabse"
- **With modifications**: "falafel without tahini", "shawarma with extra chicken 200g"

## Data Sources

- **USDA Foundation Foods**: Comprehensive nutritional database
- **USDA SR Legacy**: Standard Reference database
- **Custom Arabic Dishes**: 10+ sample dishes from various Arab countries (expandable)

## Development

### Backend Testing
```bash
cd backend
pytest
```

### Frontend Development
```bash
cd frontend
ng serve --open
```

### Building for Production
```bash
docker-compose build
```

## Notes

- GPT is used for Natural Language Understanding ONLY - calorie calculations always use USDA data
- Missing dishes are automatically logged for admin review
- The system supports conversational context for follow-up questions
- All nutritional calculations are based on ingredient weights

## Branches

| Branch | Description |
|--------|-------------|
| `main` | Base branch |
| `powered-by-ai` | GPT/DeepSeek implementation (this branch) |
| `powered-by-models` | Local ML models implementation (future) |

## License

This is a research project for academic purposes.

## Contact

For questions or contributions, please open an issue on GitHub.
