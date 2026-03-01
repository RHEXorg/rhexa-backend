import json
import os
import traceback
import pandas as pd
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_organization_access
from app.models.database_connection import DatabaseConnection
from app.models.document import Document
from app.schemas.analysis import DashboardGenerateRequest
from app.services.database_service import database_service
from app.core.ai_models import get_llm
from app.core.storage import get_storage
from langchain_core.messages import SystemMessage, HumanMessage
import logging
import re

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


# ─────────────────────────────────────────────────────────────
# UTILITY: Read file into DataFrame
# ─────────────────────────────────────────────────────────────
def _read_file_as_dataframe(file_path: str, file_type: str) -> pd.DataFrame:
    """Read a CSV or Excel file into a pandas DataFrame."""
    logger.info(f"Reading file: {file_path} (type: {file_type})")
    if file_type == "csv":
        # Try multiple encodings
        for encoding in ["utf-8", "latin-1", "cp1252", "iso-8859-1"]:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                logger.info(f"Successfully read CSV with {encoding} encoding. Shape: {df.shape}")
                return df
            except UnicodeDecodeError:
                continue
        # Final fallback
        return pd.read_csv(file_path, encoding="utf-8", errors="replace")
    elif file_type in ("xlsx", "xls"):
        df = pd.read_excel(file_path)
        logger.info(f"Successfully read Excel. Shape: {df.shape}")
        return df
    else:
        raise ValueError(f"Unsupported file type for analysis: {file_type}")


# ─────────────────────────────────────────────────────────────
# UTILITY: Clean DataFrame values for JSON serialization
# ─────────────────────────────────────────────────────────────
def _clean_value(v):
    """Convert a single value to JSON-safe type."""
    if v is None:
        return 0
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        val = float(v)
        if np.isnan(val) or np.isinf(val):
            return 0
        return val
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, (np.ndarray,)):
        return v.tolist()
    if isinstance(v, float):
        if np.isnan(v) or np.isinf(v):
            return 0
        return v
    if pd.isna(v):
        return 0
    return v


def _clean_data(data: list) -> list:
    """Make every value in a list of dicts JSON-serializable."""
    clean = []
    for row in data:
        clean_row = {}
        for k, v in row.items():
            clean_row[str(k)] = _clean_value(v)
        clean.append(clean_row)
    return clean


# ─────────────────────────────────────────────────────────────
# FALLBACK: Generate charts using pure pandas (no AI needed)
# ─────────────────────────────────────────────────────────────
def _generate_fallback_charts(df: pd.DataFrame, filename: str) -> list:
    """
    Generate smart chart configs using pure pandas analysis.
    This is the fallback when AI fails — it still produces great charts.
    """
    logger.info(f"Generating fallback charts for {filename} with shape {df.shape}")
    charts = []

    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    date_cols = []

    # Try to detect date columns
    for col in df.columns:
        if df[col].dtype == "object":
            sample = df[col].dropna().head(20)
            try:
                pd.to_datetime(sample)
                date_cols.append(col)
            except Exception:
                pass

    logger.info(f"Columns — numeric: {numeric_cols}, categorical: {categorical_cols}, date-like: {date_cols}")

    # ─── CHART 1: Top categories by count (Bar) ───
    if categorical_cols:
        cat_col = categorical_cols[0]
        vc = df[cat_col].value_counts().head(15)
        if len(vc) >= 2:
            chart_data = [{"category": str(k), "count": int(v)} for k, v in vc.items()]
            charts.append({
                "title": f"Distribution of {cat_col}",
                "type": "bar",
                "xAxisKey": "category",
                "dataKeys": ["count"],
                "data": chart_data,
                "source_file": filename
            })

    # ─── CHART 2: Numeric column distribution (Area) ───
    if numeric_cols:
        num_col = numeric_cols[0]
        # Create histogram-like buckets
        series = df[num_col].dropna()
        if len(series) > 5:
            try:
                bins = pd.cut(series, bins=min(15, max(5, len(series) // 10)), duplicates='drop')
                bin_counts = bins.value_counts().sort_index()
                chart_data = [{"range": str(interval), "count": int(count)} for interval, count in bin_counts.items()]
                if chart_data:
                    charts.append({
                        "title": f"{num_col} Distribution",
                        "type": "area",
                        "xAxisKey": "range",
                        "dataKeys": ["count"],
                        "data": chart_data,
                        "source_file": filename
                    })
            except Exception as e:
                logger.warning(f"Histogram failed for {num_col}: {e}")

    # ─── CHART 3: Category vs numeric average (Bar) ───
    if categorical_cols and numeric_cols:
        cat_col = categorical_cols[0]
        num_col = numeric_cols[0]
        unique_count = df[cat_col].nunique()
        if 2 <= unique_count <= 30:
            grouped = df.groupby(cat_col)[num_col].mean().sort_values(ascending=False).head(15)
            chart_data = [{"category": str(k), "average": round(float(v), 2)} for k, v in grouped.items()]
            if chart_data:
                charts.append({
                    "title": f"Average {num_col} by {cat_col}",
                    "type": "bar",
                    "xAxisKey": "category",
                    "dataKeys": ["average"],
                    "data": chart_data,
                    "source_file": filename
                })

    # ─── CHART 4: If 2+ numeric cols → Scatter ───
    if len(numeric_cols) >= 2:
        col_x = numeric_cols[0]
        col_y = numeric_cols[1]
        subset = df[[col_x, col_y]].dropna().head(30)
        chart_data = _clean_data(subset.to_dict(orient="records"))
        if len(chart_data) >= 5:
            charts.append({
                "title": f"{col_x} vs {col_y} Correlation",
                "type": "scatter",
                "xAxisKey": col_x,
                "dataKeys": [col_y],
                "data": chart_data,
                "source_file": filename
            })

    # ─── CHART 5: Pie chart for small-cardinality categories ───
    if categorical_cols:
        for cat_col in categorical_cols:
            unique_count = df[cat_col].nunique()
            if 2 <= unique_count <= 8:
                vc = df[cat_col].value_counts()
                chart_data = [{"category": str(k), "count": int(v)} for k, v in vc.items()]
                charts.append({
                    "title": f"{cat_col} Breakdown",
                    "type": "pie",
                    "xAxisKey": "category",
                    "dataKeys": ["count"],
                    "data": chart_data,
                    "source_file": filename
                })
                break  # Only one pie

    # ─── CHART 6: Line chart for time/date + numeric ───
    if date_cols and numeric_cols:
        date_col = date_cols[0]
        num_col = numeric_cols[0]
        try:
            temp_df = df[[date_col, num_col]].dropna().copy()
            temp_df[date_col] = pd.to_datetime(temp_df[date_col])
            temp_df = temp_df.sort_values(date_col).tail(30)
            temp_df[date_col] = temp_df[date_col].dt.strftime("%Y-%m-%d")
            chart_data = _clean_data(temp_df.to_dict(orient="records"))
            if len(chart_data) >= 3:
                charts.append({
                    "title": f"{num_col} Over Time",
                    "type": "line",
                    "xAxisKey": date_col,
                    "dataKeys": [num_col],
                    "data": chart_data,
                    "source_file": filename
                })
        except Exception as e:
            logger.warning(f"Date chart failed: {e}")

    # Return max 4 charts
    return charts[:4]


# ─────────────────────────────────────────────────────────────
# AI-POWERED: Generate charts using LLM (with fallback)
# ─────────────────────────────────────────────────────────────
def _generate_charts_from_dataframe(df: pd.DataFrame, filename: str) -> list:
    """Use AI to decide what charts to render from a DataFrame, with pandas fallback."""

    # Build a concise summary for the LLM
    summary = {
        "filename": filename,
        "rows": int(len(df)),
        "columns": [str(c) for c in df.columns.tolist()],
        "dtypes": {str(col): str(dtype) for col, dtype in df.dtypes.items()},
    }

    # Add sample data (convert everything to str for safety)
    try:
        sample = df.head(3).copy()
        for col in sample.columns:
            sample[col] = sample[col].astype(str)
        summary["sample_rows"] = sample.to_dict(orient="records")
    except Exception:
        summary["sample_rows"] = []

    # Add numeric column names
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    summary["numeric_columns"] = [str(c) for c in numeric_cols]
    summary["categorical_columns"] = [str(c) for c in categorical_cols]

    llm_base = get_llm()
    if not llm_base:
        logger.warning("No LLM available, using fallback chart generation")
        return _generate_fallback_charts(df, filename)

    # DO NOT use response_format binding — many free models don't support it
    llm = llm_base

    prompt = f"""You are a data analyst. Given this dataset info, suggest exactly 4 chart configurations.

Dataset: {filename}
Rows: {summary['rows']}
Columns: {json.dumps(summary['columns'])}
Data types: {json.dumps(summary['dtypes'])}
Numeric columns: {json.dumps(summary['numeric_columns'])}
Categorical columns: {json.dumps(summary['categorical_columns'])}
Sample data: {json.dumps(summary.get('sample_rows', []), default=str)}

Reply with ONLY a JSON object (no other text, no markdown, no explanation). The JSON must have one key "charts" containing an array of 4 objects. Each object has:
- "title": string
- "type": one of "bar", "line", "pie", "area", "scatter"
- "xAxisKey": column name for x-axis (must be from the columns list above)
- "dataKeys": array of column names for y-axis values (must be numeric columns from above)
- "aggregation": one of "none", "sum", "count", "mean"
- "limit": integer 5-25

Example response:
{{"charts":[{{"title":"Sales by Region","type":"bar","xAxisKey":"region","dataKeys":["revenue"],"aggregation":"sum","limit":10}},{{"title":"Orders Over Time","type":"line","xAxisKey":"date","dataKeys":["order_count"],"aggregation":"none","limit":20}},{{"title":"Category Split","type":"pie","xAxisKey":"category","dataKeys":["amount"],"aggregation":"sum","limit":8}},{{"title":"Price vs Quantity","type":"scatter","xAxisKey":"price","dataKeys":["quantity"],"aggregation":"none","limit":25}}]}}

RESPOND WITH ONLY THE JSON. NO OTHER TEXT."""

    try:
        logger.info(f"Sending LLM request for file analysis: {filename}")
        res = llm.invoke([
            SystemMessage(content="You output only valid JSON. No markdown, no explanation, no code blocks."),
            HumanMessage(content=prompt)
        ])

        raw_content = res.content.strip()
        logger.info(f"LLM raw response (first 500 chars): {raw_content[:500]}")

        # Aggressively extract JSON from any wrapper
        content = raw_content

        # Remove markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            parts = content.split("```")
            for part in parts:
                if "{" in part and "charts" in part:
                    content = part
                    break

        # Try to find JSON object
        json_match = re.search(r'\{[\s\S]*"charts"[\s\S]*\}', content)
        if json_match:
            content = json_match.group(0)

        content = content.strip()
        logger.info(f"Cleaned JSON content (first 500 chars): {content[:500]}")

        config = json.loads(content)
        charts = []

        for chart_def in config.get("charts", []):
            try:
                x_key = str(chart_def.get("xAxisKey", ""))
                data_keys = [str(k) for k in chart_def.get("dataKeys", [])]
                aggregation = str(chart_def.get("aggregation", "none"))
                limit = min(int(chart_def.get("limit", 20)), 30)

                if x_key not in df.columns:
                    logger.warning(f"xAxisKey '{x_key}' not in columns, skipping")
                    continue

                valid_data_keys = [k for k in data_keys if k in df.columns]

                if aggregation == "count":
                    agg_df = df[x_key].value_counts().head(limit).reset_index()
                    agg_df.columns = [x_key, "count"]
                    chart_def["dataKeys"] = ["count"]
                    chart_data = agg_df.to_dict(orient="records")
                elif aggregation in ("sum", "mean") and valid_data_keys:
                    agg_df = df.groupby(x_key)[valid_data_keys].agg(aggregation).reset_index()
                    agg_df = agg_df.sort_values(valid_data_keys[0], ascending=False).head(limit)
                    chart_data = agg_df.to_dict(orient="records")
                    chart_def["dataKeys"] = valid_data_keys
                else:
                    if valid_data_keys:
                        subset = df[[x_key] + valid_data_keys].dropna().head(limit)
                    else:
                        subset = df[[x_key]].dropna().head(limit)
                    chart_data = subset.to_dict(orient="records")
                    chart_def["dataKeys"] = valid_data_keys if valid_data_keys else ["count"]

                if not chart_data:
                    continue

                chart_def["data"] = _clean_data(chart_data)
                chart_def["source_file"] = filename
                chart_def.pop("aggregation", None)
                chart_def.pop("limit", None)
                charts.append(chart_def)

            except Exception as inner_err:
                logger.error(f"Failed to build chart: {inner_err}")

        if charts:
            logger.info(f"AI successfully generated {len(charts)} charts for {filename}")
            return charts
        else:
            logger.warning("AI generated 0 valid charts, falling back to pandas")
            return _generate_fallback_charts(df, filename)

    except json.JSONDecodeError as je:
        logger.error(f"JSON parse error: {je}. Raw: {raw_content[:300] if 'raw_content' in dir() else 'N/A'}")
        return _generate_fallback_charts(df, filename)
    except Exception as e:
        logger.error(f"AI chart generation failed: {e}\n{traceback.format_exc()}")
        return _generate_fallback_charts(df, filename)


# ─────────────────────────────────────────────────────────────
# MAIN ENDPOINT
# ─────────────────────────────────────────────────────────────
@router.post("/dashboard")
def generate_dashboard(
    request: DashboardGenerateRequest,
    db: Session = Depends(get_db),
    current_org_id: int = Depends(require_organization_access)
):
    try:
        charts = []
        storage = get_storage()

        # ────────── DATABASE SOURCES ──────────
        if request.database_ids:
            for db_id in request.database_ids:
                db_conn = db.query(DatabaseConnection).filter(
                    DatabaseConnection.id == db_id,
                    DatabaseConnection.organization_id == current_org_id
                ).first()
                if not db_conn:
                    continue

                schema = database_service.get_schema(db_conn)

                base_llm = get_llm()
                if not base_llm:
                    logger.error("No LLM configured for database analysis")
                    continue

                # Don't use response_format for compatibility
                llm = base_llm

                prompt = f"""You are a data analyst creating a dashboard from a {db_conn.db_type} database.

Schema: {json.dumps(schema)}

Generate exactly 4 SQL queries for interesting charts. Reply with ONLY a JSON object (no markdown, no explanation). The JSON has one key "charts" with an array of 4 objects. Each object has:
- "title": string
- "type": one of "bar", "line", "pie", "area", "scatter"
- "sql_query": a valid SELECT query for {db_conn.db_type}, LIMIT 30 max
- "xAxisKey": exact column alias for x-axis
- "dataKeys": array of exact column aliases for y-axis values

Example: {{"charts":[{{"title":"Top Sales","type":"bar","sql_query":"SELECT category, SUM(amount) AS total FROM orders GROUP BY category ORDER BY total DESC LIMIT 10","xAxisKey":"category","dataKeys":["total"]}}]}}

RESPOND WITH ONLY JSON."""

                try:
                    res = llm.invoke([
                        SystemMessage(content="You output only valid JSON. No markdown, no explanation."),
                        HumanMessage(content=prompt)
                    ])

                    raw = res.content.strip()
                    logger.info(f"DB LLM response (first 500): {raw[:500]}")

                    content = raw
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0]
                    elif "```" in content:
                        parts = content.split("```")
                        for part in parts:
                            if "{" in part and "charts" in part:
                                content = part
                                break

                    json_match = re.search(r'\{[\s\S]*"charts"[\s\S]*\}', content)
                    if json_match:
                        content = json_match.group(0)

                    config = json.loads(content.strip())
                    for chart_def in config.get("charts", []):
                        try:
                            data = database_service.execute_query(db_conn, chart_def["sql_query"])
                            if not data:
                                continue
                            # Clean decimal/numpy types
                            clean = _clean_data(data)
                            chart_def["data"] = clean
                            chart_def["database_name"] = db_conn.name
                            charts.append(chart_def)
                        except Exception as q_err:
                            logger.error(f"SQL exec failed: {q_err}")
                except Exception as p_err:
                    logger.error(f"DB LLM processing failed: {p_err}\n{traceback.format_exc()}")

        # ────────── FILE (DOCUMENT) SOURCES ──────────
        if request.document_ids:
            for doc_id in request.document_ids:
                document = db.query(Document).filter(
                    Document.id == doc_id,
                    Document.organization_id == current_org_id
                ).first()
                if not document:
                    logger.warning(f"Document {doc_id} not found for org {current_org_id}")
                    continue

                if document.file_type not in ("csv", "xlsx", "xls"):
                    logger.info(f"Skipping non-tabular file: {document.filename} ({document.file_type})")
                    continue

                try:
                    full_path = storage.get_full_path(document.file_path)
                    logger.info(f"Processing file: {full_path}")

                    if not os.path.exists(full_path):
                        logger.error(f"File not found on disk: {full_path}")
                        continue

                    df = _read_file_as_dataframe(full_path, document.file_type)

                    if df.empty:
                        logger.warning(f"File {document.filename} resulted in empty DataFrame")
                        continue

                    file_charts = _generate_charts_from_dataframe(df, document.filename)
                    logger.info(f"Generated {len(file_charts)} charts from {document.filename}")
                    charts.extend(file_charts)
                except Exception as file_err:
                    logger.error(f"File processing failed for {document.filename}: {file_err}\n{traceback.format_exc()}")

        logger.info(f"Total charts generated: {len(charts)}")
        return {"success": True, "charts": charts}
    except Exception as e:
        logger.exception("Dashboard generation error")
        raise HTTPException(status_code=500, detail=str(e))
