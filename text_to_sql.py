# =============================================
#  TEXT TO SQL ENGINE - FINAL VERSION
#  Phase 6: Full Error Handling & Validation
#  - Strict prompt validation
#  - Greeting detection
#  - Dangerous keyword blocking
#  - Irrelevant topic blocking
#  - Auto SQL retry on failure
#  - Friendly error messages
# =============================================

import os
import re
import sqlite3
import pandas as pd
from groq import Groq
from dotenv import load_dotenv
from schema_context import SCHEMA_CONTEXT

load_dotenv()

# ── API KEY ───────────────────────────────────────────────────
api_key = os.getenv("GROQ_API_KEY")
#api_key = "#####"  # fallback hardcode

if not api_key:
    raise ValueError("GROQ_API_KEY not found! Check your .env file.")

print(f" Groq API Key loaded: {api_key[:8]}{'*' * 20}")

client = Groq(api_key=api_key)
print(" Groq client ready!")

DB_PATH = os.getenv("DB_PATH", "healthcare_insurance.db")
print(f" Database path: {DB_PATH}")


# ── VALID TABLES ──────────────────────────────────────────────
VALID_TABLES = [
    "CLAIM", "INSURED", "POLICY", "HOSPITAL", "VENDOR",
    "TREATMENT", "CLAIM_TREATMENT", "CLAIM_VALIDATION",
    "CLAIM_PAYMENT", "HOSPITAL_NETWORK"
]

# ── HEALTHCARE DOMAIN KEYWORDS ────────────────────────────────
HEALTHCARE_KEYWORDS = [
    "claim", "insured", "policy", "hospital", "vendor", "treatment",
    "payment", "fraud", "approved", "rejected", "pending", "report",
    "amount", "network", "validation", "patient", "member", "rate",
    "cashless", "reimbursement", "tpa", "diagnosis", "surgery",
    "admission", "discharge", "premium", "coverage", "plan",
    "invoice", "bill", "doctor", "medicine", "health", "insurance",
    "beneficiary", "provider", "procedure", "preauthorization",
    "copay", "deductible", "benefit", "grievance", "maternity"
]

# ── GREETING WORDS ────────────────────────────────────────────
GREETINGS = [
    "hello", "hi", "hey", "hii", "hiii", "howdy", "sup",
    "good morning", "good evening", "good afternoon", "good night",
    "how are you", "what's up", "whats up", "how r u",
    "thanks", "thank you", "thank u", "thx",
    "ok", "okay", "k", "yes", "no", "bye", "goodbye",
    "test", "testing", "check", "ping", "yo", "what"
]

# ── DANGEROUS SQL KEYWORDS ────────────────────────────────────
DANGEROUS_WORDS = [
    "delete", "drop", "truncate", "alter", "update",
    "insert", "create", "modify", "remove", "destroy",
    "replace", "merge", "execute", "exec", "grant", "revoke"
]

# ── IRRELEVANT TOPICS ─────────────────────────────────────────
IRRELEVANT_TOPICS = [
    "weather", "cricket", "movie", "song", "recipe", "news",
    "stock", "sports", "game", "joke", "poem", "capital",
    "president", "country", "translate", "math", "calculate",
    "football", "temple", "food", "restaurant", "travel",
    "hotel", "flight", "politics", "election", "celebrity",
    "music", "dance", "art", "history", "science", "geography"
]


# ══════════════════════════════════════════════════════════════
#  STEP 1: VALIDATE PROMPT
# ══════════════════════════════════════════════════════════════
def validate_prompt(user_prompt: str) -> dict:
    """
    Strictly validates the user prompt before sending to Groq.
    Catches: too short, greetings, dangerous words, irrelevant topics.
    """
    prompt_lower = user_prompt.lower().strip()

    # ── Check 1: Too short ────────────────────────────────────
    if len(prompt_lower) < 5:
        return {
            "valid":   False,
            "reason":  "too_short",
            "message": "Please type a more detailed question.\n\nExample: 'Give me claim report' or 'Show rejected claims with hospital name'."
        }

    # ── Check 2: Greetings & random words ────────────────────
    for g in GREETINGS:
        if prompt_lower == g or prompt_lower.startswith(g + " ") or prompt_lower.startswith(g + "!"):
            return {
                "valid":   False,
                "reason":  "greeting",
                "message": "👋 Hello! I am your Healthcare Insurance Report Assistant.\n\nI can help you with:\n• Claim Reports\n• Payment Reports\n• Fraud Reports\n• Hospital Reports\n• Insured Member Reports\n\nTry: 'Give me claim report' or 'Show rejected claims'."
            }

    # ── Check 3: Dangerous SQL keywords ──────────────────────
    for word in DANGEROUS_WORDS:
        if re.search(rf"\b{word}\b", prompt_lower):
            return {
                "valid":   False,
                "reason":  "dangerous",
                "message": f"⛔ The action '{word}' is not allowed.\n\nI can only fetch and display reports — not modify or delete data.\n\nTry: 'Show vendor report' or 'Give me claim report'."
            }

    # ── Check 4: Completely irrelevant topics ─────────────────
    for word in IRRELEVANT_TOPICS:
        if re.search(rf"\b{word}\b", prompt_lower):
            return {
                "valid":   False,
                "reason":  "irrelevant",
                "message": "🏥 I can only answer questions about healthcare insurance data.\n\nI cover: Claims, Payments, Hospitals, Insured Members, Vendors, and Treatments.\n\nTry: 'Give me payment report' or 'Show fraud claims'."
            }

    # ── Check 5: Must have at least one healthcare keyword ────
    has_keyword = any(kw in prompt_lower for kw in HEALTHCARE_KEYWORDS)
    if not has_keyword:
        return {
            "valid":   False,
            "reason":  "no_keyword",
            "message": "🤔 I didn't understand that request.\n\nPlease ask about:\n• Claims & Payments\n• Hospitals & Networks\n• Insured Members & Policies\n• Vendors & Treatments\n• Fraud Indicators\n\nExample: 'Show all approved claims with hospital name'."
        }

    return {"valid": True, "reason": "ok", "message": ""}


# ══════════════════════════════════════════════════════════════
#  STEP 2: CLEAN GENERATED SQL
# ══════════════════════════════════════════════════════════════
def clean_sql(raw: str) -> str:
    """
    Strips markdown, backticks, and extra explanation text.
    """
    sql = raw.strip()
    sql = re.sub(r"```sql", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"```",    "", sql)

    # Keep only the SELECT statement — drop any explanation after LIMIT
    lines     = sql.splitlines()
    sql_lines = []
    for line in lines:
        sql_lines.append(line)
        stripped = line.strip().rstrip(";").upper()
        if stripped.startswith("LIMIT") or "LIMIT 100" in stripped:
            break

    sql = "\n".join(sql_lines).strip().rstrip(";")
    return sql


# ══════════════════════════════════════════════════════════════
#  STEP 3: GENERATE SQL FROM GROQ
# ══════════════════════════════════════════════════════════════
def prompt_to_sql(user_prompt: str, retry_hint: str = "") -> str:
    """
    Sends prompt + schema to Groq (Llama 3.3).
    On retry, passes the previous error back for self-correction.
    """
    extra = ""
    if retry_hint:
        extra = f"""
PREVIOUS ATTEMPT FAILED WITH THIS ERROR: {retry_hint}
Please carefully fix the SQL. Double-check all JOIN conditions match the schema exactly.
Remember: INSURED is NEVER joined directly to CLAIM — always go through POLICY first.
"""

    full_prompt = f"""
{SCHEMA_CONTEXT}
{extra}
USER REQUEST: "{user_prompt}"

SQL QUERY:
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a SQL expert for a healthcare insurance database. "
                    "Return ONLY the raw SQL SELECT query. "
                    "No explanation, no markdown, no backticks, no comments, no extra text. "
                    "Never use DROP, DELETE, UPDATE, INSERT, ALTER, or TRUNCATE."
                )
            },
            {
                "role": "user",
                "content": full_prompt
            }
        ],
        temperature=0,
        max_tokens=600
    )

    raw_sql = response.choices[0].message.content.strip()
    return clean_sql(raw_sql)


# ══════════════════════════════════════════════════════════════
#  STEP 4: VALIDATE SQL SAFETY
# ══════════════════════════════════════════════════════════════
def validate_sql(sql: str) -> dict:
    """
    Final safety check before executing SQL on the database.
    """
    sql_upper = sql.strip().upper()

    # Must be SELECT
    if not sql_upper.startswith("SELECT"):
        return {
            "valid":   False,
            "message": "Only SELECT queries are allowed for security reasons."
        }

    # Block dangerous keywords
    for word in ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE"]:
        if re.search(rf"\b{word}\b", sql_upper):
            return {
                "valid":   False,
                "message": f"Query contains restricted keyword: {word}. Only SELECT is permitted."
            }

    # Must reference at least one valid table
    has_table = any(t in sql_upper for t in VALID_TABLES)
    if not has_table:
        return {
            "valid":   False,
            "message": "Generated SQL does not reference any known table in the database."
        }

    return {"valid": True, "message": ""}


# ══════════════════════════════════════════════════════════════
#  STEP 5: EXECUTE SQL ON SQLITE
# ══════════════════════════════════════════════════════════════
def execute_sql(sql: str) -> dict:
    """
    Executes the SQL on the SQLite database.
    Returns structured result with rows and columns.
    """
    if not os.path.exists(DB_PATH):
        return {
            "success":   False,
            "error":     f"Database not found at: {DB_PATH}. Please check your DB_PATH in .env.",
            "sql":       sql,
            "data":      [],
            "columns":   [],
            "row_count": 0
        }

    try:
        conn = sqlite3.connect(DB_PATH)
        df   = pd.read_sql_query(sql, conn)
        conn.close()

        return {
            "success":   True,
            "sql":       sql,
            "columns":   list(df.columns),
            "data":      df.to_dict(orient="records"),
            "row_count": len(df)
        }

    except Exception as e:
        return {
            "success":   False,
            "error":     str(e),
            "sql":       sql,
            "data":      [],
            "columns":   [],
            "row_count": 0
        }


# ══════════════════════════════════════════════════════════════
#  STEP 6: FRIENDLY ERROR MESSAGES
# ══════════════════════════════════════════════════════════════
def friendly_error(error: str, prompt: str) -> str:
    """
    Converts raw SQLite error messages into user-friendly text.
    """
    err = error.lower()

    if "no such table" in err:
        table = re.search(r"no such table: (\w+)", error, re.IGNORECASE)
        name  = table.group(1) if table else "unknown"
        return f"❌ I couldn't find the table '{name}' in the database.\n\nPlease try rephrasing your question."

    if "no such column" in err:
        col  = re.search(r"no such column: (\S+)", error, re.IGNORECASE)
        name = col.group(1) if col else "unknown"
        return f"❌ I couldn't find the column '{name}'.\n\nTry rephrasing — for example: 'show claim report with hospital name'."

    if "ambiguous column" in err:
        return "❌ The query was ambiguous.\n\nPlease be more specific — for example: 'show claim number and insured name from claim report'."

    if "syntax error" in err:
        return "❌ There was a SQL syntax error. Please try rephrasing your question more clearly."

    if "database not found" in err:
        return "❌ Cannot connect to the database. Please check your DB_PATH setting in the .env file."

    if "no results" in err or "no rows" in err:
        return f"⚠️ No records found for '{prompt}'. Try a broader question like 'give me claim report'."

    return f"❌ Something went wrong: {error}\n\nPlease try rephrasing your question."


# ══════════════════════════════════════════════════════════════
#  MASTER FUNCTION — FULL PIPELINE WITH RETRY
# ══════════════════════════════════════════════════════════════
def generate_report(user_prompt: str) -> dict:
    """
    Complete pipeline:
    Prompt → Validate → SQL → Validate SQL → Execute → Retry if fail → Report
    """
    print(f"\n{'='*55}")
    print(f"[USER PROMPT]   : {user_prompt}")

    # ── STEP 1: Validate prompt ───────────────────────────────
    validation = validate_prompt(user_prompt)
    if not validation["valid"]:
        print(f"[VALIDATION]    : ❌ {validation['reason']} — {validation['message'][:60]}")
        return {
            "success":        False,
            "error":          validation["message"],
            "friendly_error": validation["message"],
            "sql":            "",
            "data":           [],
            "columns":        [],
            "row_count":      0,
            "reason":         validation["reason"]
        }

    # ── STEP 2: Generate SQL (Attempt 1) ─────────────────────
    try:
        sql = prompt_to_sql(user_prompt)
        print(f"[GENERATED SQL] : {sql}")
    except Exception as e:
        print(f"[GROQ ERROR]    : {e}")
        return {
            "success":        False,
            "error":          str(e),
            "friendly_error": "⚠️ I had trouble connecting to the AI. Please try again in a moment.",
            "sql":            "",
            "data":           [],
            "columns":        [],
            "row_count":      0
        }

    # ── STEP 3: Validate SQL safety ───────────────────────────
    sql_check = validate_sql(sql)
    if not sql_check["valid"]:
        print(f"[SQL INVALID]   : {sql_check['message']}")
        return {
            "success":        False,
            "error":          sql_check["message"],
            "friendly_error": f"⛔ {sql_check['message']}",
            "sql":            sql,
            "data":           [],
            "columns":        [],
            "row_count":      0
        }

    # ── STEP 4: Execute SQL ───────────────────────────────────
    result = execute_sql(sql)

    # ── STEP 5: Retry if failed ───────────────────────────────
    if not result["success"]:
        print(f"[ATTEMPT 1 FAIL]: {result['error']}")
        print(f"[RETRYING...]   : Sending error back to Groq for auto-fix...")

        try:
            sql2      = prompt_to_sql(user_prompt, retry_hint=result["error"])
            print(f"[RETRY SQL]     : {sql2}")

            sql_check2 = validate_sql(sql2)
            if sql_check2["valid"]:
                result2 = execute_sql(sql2)
                if result2["success"]:
                    print(f"[RETRY STATUS]  : ✅ Auto-corrected successfully!")
                    result2["retried"] = True
                    result2["sql"]     = sql2
                    return result2
                else:
                    print(f"[RETRY FAILED]  : {result2['error']}")
                    result2["friendly_error"] = friendly_error(result2["error"], user_prompt)
                    return result2

        except Exception as e:
            print(f"[RETRY ERROR]   : {e}")

        # Both attempts failed
        result["friendly_error"] = friendly_error(result["error"], user_prompt)
        return result

    # ── STEP 6: Handle empty results ─────────────────────────
    if result["success"] and result["row_count"] == 0:
        print(f"[STATUS]        :  Query ran but 0 rows returned")
        result["friendly_error"] = (
            f"⚠️ No records found for '{user_prompt}'.\n\n"
            f"The query ran successfully but returned no data. "
            f"Try a broader question like 'give me claim report'."
        )
        return result

    print(f"[STATUS]        :  Success — {result['row_count']} rows returned")
    return result


# ══════════════════════════════════════════════════════════════
#  TEST (run directly: python text_to_sql.py)
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    test_prompts = [
        #  Valid prompts
        "give me claim report",
        "show all rejected claims with insured name and hospital name",
        "list all high fraud indicator claims with insured name",
        "give me payment report with insured name and paid amount",
        # ❌ Should be blocked
        "hello",
        "hi",
        "delete the table vendor report",
        "what is the weather today",
        "show me cricket scores",
        "good morning",
        "test",
    ]

    print("\n" + "="*55)
    print("  RUNNING ALL TEST PROMPTS")
    print("="*55)

    for prompt in test_prompts:
        result = generate_report(prompt)
        if result["success"] and result["row_count"] > 0:
            print(f"[✅ ROWS]        : {result['row_count']} rows")
        else:
            msg = result.get("friendly_error") or result.get("error", "Unknown error")
            print(f"[❌ BLOCKED]     : {msg[:80]}")

    print("\n" + "="*55)
    print("  ALL TESTS COMPLETE!")
    print("="*55)
