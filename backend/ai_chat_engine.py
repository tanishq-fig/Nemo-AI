"""
AI Chat Engine — Gemini-powered ARGO data assistant.

Two-step pipeline:
  1. Analyze user query → decide whether SQL is needed, generate it, pick chart type.
  2. Execute SQL (if any) → send results + original query to Gemini for natural language answer.

The response text intentionally includes chart-type keywords so the existing
frontend chart-detection logic (`detectChartsFromResponse`) triggers automatically.
"""

import json
import re
import traceback
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import text

from config import settings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TABLE_NAME = "argo_profiles"

SCHEMA_DESCRIPTION = """
DATA SOURCE: Live ARGO ocean data via IFREMER ERDDAP API + local SQLite cache.

TABLE: argo_profiles
COLUMNS:
  id            INTEGER  PRIMARY KEY
  temperature   REAL     (°C, ocean water temperature, may be NULL)
  salinity      REAL     (PSU, practical salinity units, may be NULL)
  depth         REAL     (meters, measurement depth, may be NULL)
  latitude      REAL     (degrees, -90 to 90)
  longitude     REAL     (degrees, -180 to 180)
  timestamp     DATETIME (ISO-8601, measurement time, may be NULL)
  float_id      TEXT     (unique ARGO float identifier)
  cycle_number  INTEGER  (measurement cycle within a float, may be NULL)
  pressure      REAL     (dbar, ocean pressure, may be NULL)

NOTES:
- This is a SQLite database backed by live ERDDAP data. Use SQLite-compatible SQL only.
- Always use argo_profiles as the table name.
- Temperature, salinity, depth may have NULLs; filter with IS NOT NULL when computing aggregates.
- latitude/longitude are always present.
- Data is refreshed from IFREMER ERDDAP (erddap.ifremer.fr) periodically.
"""

CHART_TYPE_GUIDE = """
Available chart keywords the frontend recognises (include one in your answer when a chart helps):
  temperature_histogram  — histogram of temperature values
  salinity_histogram     — histogram of salinity values
  depth_profile          — depth vs temperature line plot
  scatter_plot           — temperature vs salinity T-S scatter
  heatmap                — geographic spatial distribution map
  3d_scatter             — 3-D scatter of temperature/salinity/depth
  line_chart / time_series — line chart of a variable over measurement index
  correlation            — correlation heatmap matrix

When recommending, embed the keyword naturally, e.g.:
"Here's a temperature_histogram showing the spread across all profiles."
"""

SYSTEM_PROMPT_STEP1 = f"""You are ARGO-AI, a smart oceanographic data assistant.
You have access to a single SQLite table of ARGO float measurements.

{SCHEMA_DESCRIPTION}

TASK: Given a user question, decide how to answer it.

RULES:
1. If the question needs data from the database, produce a valid SQLite SELECT query.
   - Only SELECT statements are allowed. Never write INSERT/UPDATE/DELETE/DROP/ALTER/CREATE.
   - Use aggregate functions (AVG, MIN, MAX, COUNT, SUM) where appropriate.
   - LIMIT results to at most 200 rows unless the user explicitly asks for more.
   - When the question is vague, default to useful summary statistics.
2. If the question is conversational (greeting, clarification, etc.), set sql to null.
3. Pick a chart_type from the list below if a visualisation would help, otherwise null.
   Chart types: temperature_histogram, salinity_histogram, depth_profile, scatter_plot,
                heatmap, 3d_scatter, line_chart, correlation
4. Respond ONLY with valid JSON — no markdown fences, no extra text.

OUTPUT FORMAT (strict JSON):
{{
  "sql": "<SELECT ...>" or null,
  "chart_type": "<chart_keyword>" or null,
  "reasoning": "one sentence about your approach"
}}
"""

SYSTEM_PROMPT_STEP2 = f"""You are ARGO-AI, a friendly and knowledgeable oceanographic data assistant.
{SCHEMA_DESCRIPTION}

{CHART_TYPE_GUIDE}

RULES FOR YOUR ANSWER:
1. Answer the user's question using the SQL results provided.
2. Be specific: cite numbers, ranges, counts from the data.
3. Use Markdown-like formatting (bold via **, bullet lists) for readability.
4. If a chart_type was selected, weave the keyword naturally into your prose so the
   frontend can detect it (e.g. "Below is a temperature_histogram of the data.").
5. Keep answers concise but thorough — aim for 100-250 words.
6. If the SQL returned no rows, say so clearly and suggest a refined question.
7. For greetings or simple questions without SQL data, just reply naturally as an ocean data assistant.
"""


# ---------------------------------------------------------------------------
# Engine class
# ---------------------------------------------------------------------------


class AIChatEngine:
    """Gemini-powered chat engine for ARGO oceanographic data.
    
    Falls back to a smart SQL-based approach if Gemini is unavailable.
    """

    def __init__(self):
        self.client = None
        self.model_name = "gemini-2.0-flash"
        self._llm_available = False

        api_key = settings.GEMINI_API_KEY
        if api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self.client = genai.GenerativeModel(self.model_name)
                self._llm_available = True
                print(f"[OK] AIChatEngine initialised (Gemini {self.model_name})")
            except Exception as e:
                print(f"[WARN] Gemini client init failed: {e}")
        else:
            print("[WARN] GEMINI_API_KEY not set - running in local-SQL fallback mode")

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def query(self, user_query: str, db: Session) -> Dict[str, Any]:
        """
        Full pipeline: analyse → (optionally) run SQL → generate answer.
        Tries live ERDDAP analytics first for chart-oriented queries,
        then falls back to SQL-based approach.
        """
        try:
            # Check if query maps directly to an ERDDAP analytics endpoint
            erddap_result = self._try_erddap_analytics(user_query)
            if erddap_result is not None:
                return erddap_result

            # ---- Step 1: Plan (Gemini or local fallback) ----
            if self._llm_available:
                plan = self._step1_plan_gpt(user_query)
            else:
                plan = self._step1_plan_local(user_query)

            sql = plan.get("sql")
            chart_type = plan.get("chart_type")
            reasoning = plan.get("reasoning", "")

            # ---- Step 2: Execute SQL (if any) ----
            sql_results: Optional[List[Dict]] = None
            sql_columns: Optional[List[str]] = None
            sql_error: Optional[str] = None
            executed_sql: Optional[str] = None

            if sql:
                validation = self._validate_sql(sql)
                if validation is not None:
                    sql_error = validation
                else:
                    executed_sql = sql
                    sql_results, sql_columns, sql_error = self._execute_sql(sql, db)

            # ---- Step 3: Generate answer (Gemini or local) ----
            if self._llm_available:
                response_text = self._step2_answer_gpt(
                    user_query=user_query,
                    sql=executed_sql,
                    sql_results=sql_results,
                    sql_columns=sql_columns,
                    sql_error=sql_error,
                    chart_type=chart_type,
                )
            else:
                response_text = self._step2_answer_local(
                    user_query=user_query,
                    sql_results=sql_results,
                    sql_columns=sql_columns,
                    sql_error=sql_error,
                    chart_type=chart_type,
                )

            # Build context list
            contexts: List[str] = []
            if executed_sql:
                contexts.append(f"SQL: {executed_sql}")
            if sql_results is not None:
                preview = json.dumps(sql_results[:5], default=str)
                contexts.append(f"Results preview: {preview}")
            if reasoning:
                contexts.append(f"Reasoning: {reasoning}")

            return {
                "query": user_query,
                "response": response_text,
                "retrieved_contexts": contexts,
                "document_ids": [],
            }

        except Exception as exc:
            traceback.print_exc()
            # If Gemini threw a quota/rate error, disable it and retry locally
            err_str = str(exc).lower()
            if self._llm_available and ("quota" in err_str or "429" in err_str or "rate" in err_str or "resource" in err_str or "invalid" in err_str or "api_key" in err_str or "api key" in err_str):
                print(f"[WARN] Gemini API error - switching to local fallback: {err_str[:120]}")
                self._llm_available = False
                return self.query(user_query, db)  # retry in fallback mode

            return {
                "query": user_query,
                "response": (
                    "I'm sorry - I encountered an error while processing your question. "
                    "Please try again or rephrase.\n\n"
                    f"Details: {exc}"
                ),
                "retrieved_contexts": [],
                "document_ids": [],
            }

    # ------------------------------------------------------------------
    # Step 1 — Plan (GPT version)
    # ------------------------------------------------------------------

    def _step1_plan_gpt(self, user_query: str) -> Dict[str, Any]:
        """Ask Gemini to produce a JSON plan: sql, chart_type, reasoning."""
        prompt = f"{SYSTEM_PROMPT_STEP1}\n\nUser question: {user_query}"

        response = self.client.generate_content(
            prompt,
            generation_config={"temperature": 0.2, "max_output_tokens": 500},
            request_options={"timeout": 10},
        )
        raw = response.text.strip()

        # Strip markdown fences if Gemini wraps them
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        try:
            plan = json.loads(raw)
        except json.JSONDecodeError:
            print(f"[WARN] Could not parse Step-1 JSON, falling back.\nRaw: {raw}")
            plan = {"sql": None, "chart_type": None, "reasoning": "parse-error"}

        return plan

    # ------------------------------------------------------------------
    # Step 1 — Plan (local keyword-based fallback)
    # ------------------------------------------------------------------

    def _step1_plan_local(self, user_query: str) -> Dict[str, Any]:
        """Map user query to SQL + chart type using keyword rules."""
        q = user_query.lower().strip()

        # Greetings / conversational
        greetings = ["hi", "hello", "hey", "greetings", "good morning", "good afternoon",
                      "good evening", "thanks", "thank you", "bye"]
        if q in greetings or (len(q.split()) <= 2 and not any(
            w in q for w in ["temperature", "salinity", "depth", "data", "show",
                             "what", "how", "count", "average", "mean", "max", "min"]
        )):
            return {"sql": None, "chart_type": None, "reasoning": "greeting"}

        sql = None
        chart_type = None

        # --- Temperature queries ---
        if "average" in q and "temperature" in q:
            sql = "SELECT ROUND(AVG(temperature), 2) as avg_temp, ROUND(MIN(temperature), 2) as min_temp, ROUND(MAX(temperature), 2) as max_temp, COUNT(*) as total FROM argo_profiles WHERE temperature IS NOT NULL"
        elif "temperature" in q and ("distribution" in q or "histogram" in q):
            sql = "SELECT temperature FROM argo_profiles WHERE temperature IS NOT NULL LIMIT 200"
            chart_type = "temperature_histogram"
        elif "hottest" in q or ("highest" in q and "temperature" in q) or ("warmest" in q):
            sql = "SELECT temperature, latitude, longitude, depth, float_id, timestamp FROM argo_profiles WHERE temperature IS NOT NULL ORDER BY temperature DESC LIMIT 10"
        elif "coldest" in q or ("lowest" in q and "temperature" in q):
            sql = "SELECT temperature, latitude, longitude, depth, float_id, timestamp FROM argo_profiles WHERE temperature IS NOT NULL ORDER BY temperature ASC LIMIT 10"

        # --- Salinity queries ---
        elif "average" in q and "salinity" in q:
            sql = "SELECT ROUND(AVG(salinity), 2) as avg_sal, ROUND(MIN(salinity), 2) as min_sal, ROUND(MAX(salinity), 2) as max_sal, COUNT(*) as total FROM argo_profiles WHERE salinity IS NOT NULL"
        elif "salinity" in q and ("distribution" in q or "histogram" in q):
            sql = "SELECT salinity FROM argo_profiles WHERE salinity IS NOT NULL LIMIT 200"
            chart_type = "salinity_histogram"

        # --- Depth queries ---
        elif "deepest" in q or ("maximum" in q and "depth" in q):
            sql = "SELECT depth, temperature, salinity, latitude, longitude, float_id FROM argo_profiles WHERE depth IS NOT NULL ORDER BY depth DESC LIMIT 10"
        elif "depth" in q and ("profile" in q or "vertical" in q):
            sql = "SELECT depth, temperature, salinity FROM argo_profiles WHERE depth IS NOT NULL AND temperature IS NOT NULL ORDER BY depth ASC LIMIT 200"
            chart_type = "depth_profile"

        # --- Float queries ---
        elif "float" in q and ("how many" in q or "count" in q or "list" in q):
            sql = "SELECT float_id, COUNT(*) as profiles, ROUND(AVG(temperature), 2) as avg_temp, ROUND(AVG(salinity), 2) as avg_sal FROM argo_profiles WHERE float_id IS NOT NULL GROUP BY float_id ORDER BY profiles DESC"
        elif "float" in q:
            # Info about a specific float
            fid_match = re.search(r'(f\d+)', q, re.IGNORECASE)
            if fid_match:
                fid = fid_match.group(1).upper()
                sql = f"SELECT float_id, COUNT(*) as profiles, ROUND(AVG(temperature),2) as avg_temp, ROUND(MIN(temperature),2) as min_temp, ROUND(MAX(temperature),2) as max_temp, ROUND(AVG(salinity),2) as avg_sal, ROUND(AVG(depth),2) as avg_depth FROM argo_profiles WHERE float_id = '{fid}'"

        # --- General stats ---
        elif "how many" in q and ("profile" in q or "measurement" in q or "record" in q or "data" in q):
            sql = "SELECT COUNT(*) as total_profiles, COUNT(DISTINCT float_id) as total_floats FROM argo_profiles"
        elif "summary" in q or "overview" in q or "statistics" in q or "stats" in q:
            sql = ("SELECT COUNT(*) as total, COUNT(DISTINCT float_id) as floats, "
                   "ROUND(AVG(temperature),2) as avg_temp, ROUND(MIN(temperature),2) as min_temp, ROUND(MAX(temperature),2) as max_temp, "
                   "ROUND(AVG(salinity),2) as avg_sal, ROUND(AVG(depth),2) as avg_depth "
                   "FROM argo_profiles")

        # --- Chart-oriented queries ---
        elif "scatter" in q or ("correlation" in q and "chart" not in q):
            sql = "SELECT temperature, salinity FROM argo_profiles WHERE temperature IS NOT NULL AND salinity IS NOT NULL LIMIT 200"
            chart_type = "scatter_plot"
        elif "heatmap" in q or "spatial" in q or ("map" in q and "distribution" in q):
            sql = "SELECT latitude, longitude, temperature FROM argo_profiles WHERE temperature IS NOT NULL LIMIT 200"
            chart_type = "heatmap"
        elif "3d" in q:
            sql = "SELECT temperature, salinity, depth FROM argo_profiles WHERE temperature IS NOT NULL AND salinity IS NOT NULL AND depth IS NOT NULL LIMIT 200"
            chart_type = "3d_scatter"
        elif "trend" in q or "time" in q:
            sql = "SELECT temperature, timestamp FROM argo_profiles WHERE temperature IS NOT NULL AND timestamp IS NOT NULL ORDER BY timestamp LIMIT 200"
            chart_type = "line_chart"
        elif "correlation" in q:
            chart_type = "correlation"

        # --- Default: general query about the data ---
        elif any(w in q for w in ["temperature", "salinity", "depth", "pressure"]):
            sql = ("SELECT COUNT(*) as total, COUNT(DISTINCT float_id) as floats, "
                   "ROUND(AVG(temperature),2) as avg_temp, ROUND(MIN(temperature),2) as min_temp, ROUND(MAX(temperature),2) as max_temp, "
                   "ROUND(AVG(salinity),2) as avg_sal, ROUND(MIN(salinity),2) as min_sal, ROUND(MAX(salinity),2) as max_sal, "
                   "ROUND(AVG(depth),2) as avg_depth, ROUND(MAX(depth),2) as max_depth "
                   "FROM argo_profiles")
        else:
            # Try a general summary for unknown queries
            sql = ("SELECT COUNT(*) as total_profiles, COUNT(DISTINCT float_id) as total_floats, "
                   "ROUND(AVG(temperature),2) as avg_temp, ROUND(AVG(salinity),2) as avg_sal, "
                   "ROUND(AVG(depth),2) as avg_depth FROM argo_profiles")

        return {
            "sql": sql,
            "chart_type": chart_type,
            "reasoning": "local-keyword-match",
        }

    # ------------------------------------------------------------------
    # SQL validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_sql(sql: str) -> Optional[str]:
        """Return an error message if the SQL is unsafe, else None."""
        sql_upper = sql.strip().upper()

        # Must start with SELECT
        if not sql_upper.startswith("SELECT"):
            return "Only SELECT queries are allowed."

        # Block dangerous keywords
        blocked = [
            "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
            "REPLACE", "TRUNCATE", "EXEC", "ATTACH", "DETACH", "PRAGMA",
        ]
        # Tokenise crudely to avoid false positives inside strings
        tokens = re.findall(r"[A-Z_]+", sql_upper)
        for kw in blocked:
            if kw in tokens:
                return f"Blocked keyword detected: {kw}"

        # Must reference our table
        if TABLE_NAME not in sql.lower():
            return f"Query must reference the '{TABLE_NAME}' table."

        return None

    # ------------------------------------------------------------------
    # SQL execution
    # ------------------------------------------------------------------

    @staticmethod
    def _execute_sql(
        sql: str, db: Session
    ) -> Tuple[Optional[List[Dict]], Optional[List[str]], Optional[str]]:
        """
        Execute a SELECT query safely.
        Returns (rows_as_dicts, column_names, error_or_None).
        """
        try:
            result = db.execute(text(sql))
            columns = list(result.keys())
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            return rows, columns, None
        except Exception as exc:
            return None, None, str(exc)

    # ------------------------------------------------------------------
    # Step 2 — Answer (GPT version)
    # ------------------------------------------------------------------

    def _step2_answer_gpt(
        self,
        user_query: str,
        sql: Optional[str],
        sql_results: Optional[List[Dict]],
        sql_columns: Optional[List[str]],
        sql_error: Optional[str],
        chart_type: Optional[str],
    ) -> str:
        """Ask Gemini to produce a polished natural-language answer."""

        parts: List[str] = [f"USER QUESTION: {user_query}"]

        if sql:
            parts.append(f"\nSQL EXECUTED:\n{sql}")
        if sql_error:
            parts.append(f"\nSQL ERROR: {sql_error}")
        if sql_results is not None:
            n = len(sql_results)
            preview = sql_results[:30]
            parts.append(
                f"\nQUERY RETURNED {n} ROW(S). First {min(n, 30)} rows:\n"
                + json.dumps(preview, indent=2, default=str)
            )
        if chart_type:
            parts.append(
                f"\nCHART RECOMMENDATION: Incorporate the keyword '{chart_type}' "
                f"naturally in your answer so the frontend displays the chart."
            )

        user_message = "\n".join(parts)
        prompt = f"{SYSTEM_PROMPT_STEP2}\n\n{user_message}"

        response = self.client.generate_content(
            prompt,
            generation_config={"temperature": 0.5, "max_output_tokens": 800},
            request_options={"timeout": 15},
        )

        return response.text.strip()

    # ------------------------------------------------------------------
    # Step 2 — Answer (local fallback)
    # ------------------------------------------------------------------

    def _step2_answer_local(
        self,
        user_query: str,
        sql_results: Optional[List[Dict]],
        sql_columns: Optional[List[str]],
        sql_error: Optional[str],
        chart_type: Optional[str],
    ) -> str:
        """Build a readable answer from SQL results without GPT."""
        q = user_query.lower()

        # Greetings
        if sql_results is None and sql_error is None:
            return (
                "Hello! I'm your **ARGO Ocean Data Assistant**. I can answer questions "
                "about ocean temperature, salinity, depth profiles, and more.\n\n"
                "Try asking things like:\n"
                "• What is the average temperature?\n"
                "• Show me a temperature histogram\n"
                "• How many floats are in the dataset?\n"
                "• What are the deepest measurements?\n"
                "• Show me a scatter plot of temperature vs salinity"
            )

        if sql_error:
            return f"I tried to query the database but ran into an issue:\n\n`{sql_error}`\n\nPlease try rephrasing your question."

        if not sql_results:
            return "The query returned no results. The data might not cover what you asked about. Try a broader question."

        # Format results intelligently
        parts: List[str] = ["Based on the ARGO oceanographic data:\n"]

        # Single aggregate row
        if len(sql_results) == 1 and len(sql_results[0]) <= 12:
            row = sql_results[0]
            for key, val in row.items():
                label = key.replace("_", " ").title()
                if val is not None:
                    if isinstance(val, float):
                        parts.append(f"• **{label}**: {val:.2f}")
                    else:
                        parts.append(f"• **{label}**: {val}")
        else:
            # Multiple rows — show as a small table / list
            n = len(sql_results)
            parts.append(f"Found **{n}** result(s):\n")
            for i, row in enumerate(sql_results[:15]):
                items = [f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}"
                         for k, v in row.items() if v is not None]
                parts.append(f"{i+1}. {', '.join(items)}")
            if n > 15:
                parts.append(f"\n... and {n - 15} more rows.")

        # Chart recommendation
        if chart_type:
            chart_labels = {
                "temperature_histogram": "temperature_histogram",
                "salinity_histogram": "salinity_histogram",
                "depth_profile": "depth_profile",
                "scatter_plot": "scatter_plot",
                "heatmap": "heatmap",
                "3d_scatter": "3d_scatter",
                "line_chart": "line chart",
                "correlation": "correlation",
            }
            label = chart_labels.get(chart_type, chart_type)
            parts.append(f"\nHere's a {label} to visualise the data.")

        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_engine: Optional[AIChatEngine] = None


def get_ai_chat_engine() -> AIChatEngine:
    """Get or create the global AIChatEngine instance."""
    global _engine
    if _engine is None:
        _engine = AIChatEngine()
    return _engine


# ---------------------------------------------------------------------------
# ERDDAP analytics helper (patched onto AIChatEngine)
# ---------------------------------------------------------------------------

def _try_erddap_analytics(self, user_query: str) -> Optional[Dict[str, Any]]:
    """Check if the user query maps to a direct ERDDAP analytics call.
    Returns a chat-response dict if matched, else None."""
    try:
        from erddap_service import get_erddap_service
        svc = get_erddap_service()
    except Exception:
        return None

    q = user_query.lower()

    result = None
    chart_kw = None

    if ("temperature" in q or "temp" in q) and ("distribution" in q or "histogram" in q):
        result = svc.temperature_distribution(limit=2000)
        chart_kw = "temperature_histogram"
    elif ("salinity" in q or "salt" in q) and ("distribution" in q or "histogram" in q):
        result = svc.salinity_distribution(limit=2000)
        chart_kw = "salinity_histogram"
    elif ("scatter" in q or "t-s" in q or "ts diagram" in q or
          ("temperature" in q and "salinity" in q and ("vs" in q or "relation" in q or "plot" in q))):
        result = svc.temp_salinity(limit=2000)
        chart_kw = "scatter_plot"
    elif ("depth" in q and ("profile" in q or "vertical" in q)) or ("temperature" in q and "depth" in q):
        result = svc.temp_depth(limit=2000)
        chart_kw = "depth_profile"
    elif "map" in q and ("location" in q or "float" in q or "where" in q):
        result = svc.map_data(limit=1000)
        chart_kw = "heatmap"
    elif "trend" in q or "time series" in q or "over time" in q:
        var = "psal" if "salinity" in q else "temp"
        result = svc.time_trends(variable=var, limit=3000, days=90)
        chart_kw = "line_chart"
    elif "3d" in q or "three dim" in q:
        result = svc.chart_data_3d_scatter(limit=1000)
        chart_kw = "3d_scatter"
    elif "correlation" in q and "matrix" in q:
        result = svc.chart_data_correlation(limit=1000)
        chart_kw = "correlation"

    if result is None:
        return None

    # Build a natural-language response
    stats = result.get("stats", {})
    data = result.get("data", [])
    n = len(data) if isinstance(data, list) else sum(len(v) for v in data.values() if isinstance(v, list))

    parts = [f"Here's a **{chart_kw}** based on **live ERDDAP data** ({n:,} measurements).\n"]
    if stats:
        if "mean" in stats:
            parts.append(f"- **Mean**: {stats['mean']}")
        if "min" in stats and "max" in stats:
            parts.append(f"- **Range**: {stats['min']} to {stats['max']}")
        if "std" in stats:
            parts.append(f"- **Std Dev**: {stats['std']}")
    corr = result.get("correlation")
    if corr is not None and chart_kw == "scatter_plot":
        parts.append(f"- **Correlation**: {corr}")
    parts.append(f"\nData sourced from IFREMER ERDDAP (erddap.ifremer.fr/erddap/tabledap/ArgoFloats).")

    return {
        "query": user_query,
        "response": "\n".join(parts),
        "retrieved_contexts": [f"ERDDAP live data: {n} records", f"Chart: {chart_kw}"],
        "document_ids": [],
    }


# Attach the method to the class
AIChatEngine._try_erddap_analytics = _try_erddap_analytics
