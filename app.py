# =============================================
#  FASTAPI BACKEND - PHASE 6
#  Added: Friendly errors, validation response
# =============================================

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from text_to_sql import generate_report
import uvicorn

app = FastAPI(
    title="Healthcare Insurance Report Chatbot",
    description="AI-powered chatbot — Natural language to SQL reports",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ────────────────────────────────────────────────────
class PromptRequest(BaseModel):
    prompt: str

class ReportResponse(BaseModel):
    success:       bool
    prompt:        str
    sql:           str
    columns:       list
    data:          list
    row_count:     int    = 0
    error:         str    = ""
    friendly_error:str    = ""
    retried:       bool   = False


# ── Routes ────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "message": "HealthClaim AI API is running!",
        "version": "2.0.0 — Phase 6",
        "status":  "healthy"
    }


@app.post("/report", response_model=ReportResponse)
def get_report(request: PromptRequest):
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    result = generate_report(request.prompt)

    return ReportResponse(
        success=        result["success"],
        prompt=         request.prompt,
        sql=            result.get("sql",            ""),
        columns=        result.get("columns",        []),
        data=           result.get("data",           []),
        row_count=      result.get("row_count",       0),
        error=          result.get("error",          ""),
        friendly_error= result.get("friendly_error", ""),
        retried=        result.get("retried",        False),
    )


@app.get("/health")
def health():
    return {"status": "healthy", "phase": 6}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
