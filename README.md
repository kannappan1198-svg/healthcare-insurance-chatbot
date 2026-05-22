# healthcare-insurance-chatbot
AI powered healthcare insurance report chatbot using Groq + SQLite
# 🏥 Healthcare Insurance AI Chatbot

An AI-powered chatbot that converts natural language into SQL queries
and returns live reports from a Healthcare Insurance database.

## Features
- Natural Language → SQL using Groq (Llama 3.3)
- 10-table Healthcare Insurance database
- Interactive Chat UI with dark theme
- Charts, Excel & CSV export
- Fraud detection reports
- Smart error handling & retry logic

## Tech Stack
| Layer | Technology |
|---|---|
| LLM | Groq API (Llama 3.3 70B) |
| Backend | Python + FastAPI |
| Database | SQLite |
| Frontend | HTML + CSS + JS + Chart.js |

## Setup
1. Clone the repo
2. Install dependencies: `pip install -r requirements.txt`
3. Create `.env` file with your `GROQ_API_KEY`
4. Run: `uvicorn app:app --reload`
5. Open `index.html` in browser

## Sample Queries
- "Give me claim report"
- "Show rejected claims with hospital name"
- "List high fraud indicator claims"
- "Payment report with insured name"

