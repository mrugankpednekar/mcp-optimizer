from __future__ import annotations

import base64
import csv
import io
import json
from typing import Any, Dict, List, Optional

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


def parse_data_file(
    file_content: str,
    file_format: str = "auto",
    encoding: str = "utf-8",
    is_base64: bool = False,
) -> Dict[str, Any]:
    """
    Parse a data file into a structured format.

    Args:
        file_content: The file content as string (plain text or base64)
        file_format: File format ('csv', 'json', 'excel', 'xlsx', 'auto')
        encoding: Text encoding (default: utf-8)
        is_base64: Whether the content is base64 encoded

    Returns:
        Dictionary with parsed data:
        - 'data': List of dictionaries (for tabular data) or dict (for JSON)
        - 'columns': List of column names (for tabular data)
        - 'rows': Number of rows (for tabular data)
        - 'format': Detected format
    """
    # Decode base64 if needed
    if is_base64:
        try:
            decoded = base64.b64decode(file_content)
            content = decoded.decode(encoding)
        except Exception as e:
            raise ValueError(f"Failed to decode base64 content: {e}")
    else:
        content = file_content

    # Auto-detect format if needed
    if file_format == "auto":
        file_format = _detect_format(content)

    # Parse based on format
    if file_format in ("csv", "tsv"):
        delimiter = "\t" if file_format == "tsv" else ","
        return _parse_csv(content, delimiter)
    elif file_format in ("json", "jsonl"):
        return _parse_json(content, is_jsonl=(file_format == "jsonl"))
    elif file_format in ("excel", "xlsx", "xls"):
        return _parse_excel(content, is_base64=is_base64)
    else:
        # Try to parse as plain text table
        return _parse_text_table(content)


def _detect_format(content: str) -> str:
    """Auto-detect file format from content."""
    content_stripped = content.strip()

    # Check for JSON
    if content_stripped.startswith("{") or content_stripped.startswith("["):
        try:
            json.loads(content_stripped)
            return "json"
        except:
            pass

    # Check for CSV (has commas and newlines)
    if "," in content and "\n" in content:
        lines = content.split("\n")
        if len(lines) > 1 and "," in lines[0]:
            return "csv"

    # Check for TSV
    if "\t" in content and "\n" in content:
        return "tsv"

    # Default to text table
    return "text"


def _parse_csv(content: str, delimiter: str = ",") -> Dict[str, Any]:
    """Parse CSV content."""
    reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
    rows = list(reader)
    if not rows:
        return {"data": [], "columns": [], "rows": 0, "format": "csv"}

    columns = list(rows[0].keys())
    
    # Try to convert numeric values
    processed_rows = []
    for row in rows:
        processed_row = {}
        for key, value in row.items():
            # Try to convert to number if possible
            try:
                if "." in value:
                    processed_row[key] = float(value)
                else:
                    processed_row[key] = int(value)
            except (ValueError, TypeError):
                processed_row[key] = value
        processed_rows.append(processed_row)
    
    return {
        "data": processed_rows,
        "columns": columns,
        "rows": len(processed_rows),
        "format": "csv",
    }


def _parse_json(content: str, is_jsonl: bool = False) -> Dict[str, Any]:
    """Parse JSON or JSONL content."""
    if is_jsonl:
        rows = []
        for line in content.strip().split("\n"):
            if line.strip():
                rows.append(json.loads(line))
        if not rows:
            return {"data": [], "columns": [], "rows": 0, "format": "jsonl"}
        # Extract columns from first row
        columns = list(rows[0].keys()) if isinstance(rows[0], dict) else []
        return {
            "data": rows,
            "columns": columns,
            "rows": len(rows),
            "format": "jsonl",
        }
    else:
        parsed = json.loads(content)
        if isinstance(parsed, list):
            if not parsed:
                return {"data": [], "columns": [], "rows": 0, "format": "json"}
            columns = list(parsed[0].keys()) if isinstance(parsed[0], dict) else []
            return {
                "data": parsed,
                "columns": columns,
                "rows": len(parsed),
                "format": "json",
            }
        elif isinstance(parsed, dict):
            return {
                "data": parsed,
                "columns": list(parsed.keys()),
                "rows": 1,
                "format": "json",
            }
        else:
            return {"data": parsed, "columns": [], "rows": 1, "format": "json"}


def _parse_excel(content: str, is_base64: bool = False) -> Dict[str, Any]:
    """Parse Excel content."""
    if not HAS_PANDAS:
        raise ValueError(
            "Excel parsing requires pandas. Install with: pip install pandas openpyxl"
        )

    try:
        if is_base64:
            decoded = base64.b64decode(content)
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            # Try to read as if content is already bytes
            df = pd.read_excel(io.BytesIO(content.encode("utf-8")))
    except Exception:
        # Fallback: try reading from string
        df = pd.read_excel(io.StringIO(content))

    rows = df.to_dict("records")
    return {
        "data": rows,
        "columns": list(df.columns),
        "rows": len(rows),
        "format": "excel",
    }


def _parse_text_table(content: str) -> Dict[str, Any]:
    """Parse plain text table (space or tab separated)."""
    lines = [line.strip() for line in content.split("\n") if line.strip()]
    if not lines:
        return {"data": [], "columns": [], "rows": 0, "format": "text"}

    # Try to detect delimiter
    first_line = lines[0]
    if "\t" in first_line:
        delimiter = "\t"
    elif "|" in first_line:
        delimiter = "|"
    else:
        # Try to split by multiple spaces
        parts = [p.strip() for p in first_line.split() if p.strip()]
        if len(parts) > 1:
            # Reconstruct as simple list
            data = []
            for line in lines:
                parts = [p.strip() for p in line.split() if p.strip()]
                if parts:
                    data.append(parts)
            if data:
                # Use first row as headers if it looks like headers
                if all(not p.replace(".", "").replace("-", "").isdigit() for p in data[0]):
                    columns = data[0]
                    rows = [dict(zip(columns, row)) for row in data[1:] if len(row) == len(columns)]
                else:
                    columns = [f"col_{i}" for i in range(len(data[0]))]
                    rows = [dict(zip(columns, row)) for row in data if len(row) == len(columns)]
                return {
                    "data": rows,
                    "columns": columns,
                    "rows": len(rows),
                    "format": "text",
                }
        return {"data": content, "columns": [], "rows": 1, "format": "text"}

    # Parse with delimiter
    reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
    rows = list(reader)
    if not rows:
        return {"data": [], "columns": [], "rows": 0, "format": "text"}

    columns = list(rows[0].keys())
    return {
        "data": rows,
        "columns": columns,
        "rows": len(rows),
        "format": "text",
    }


def format_data_summary(parsed_data: Dict[str, Any]) -> str:
    """
    Format parsed data into a human-readable summary for use in problem descriptions.

    Args:
        parsed_data: Output from parse_data_file

    Returns:
        Formatted string summary
    """
    if parsed_data["format"] in ("json", "jsonl") and not isinstance(parsed_data["data"], list):
        # Single JSON object
        return f"Data: {json.dumps(parsed_data['data'], indent=2)}"

    if parsed_data["rows"] == 0:
        return "Empty dataset"

    columns = parsed_data.get("columns", [])
    data = parsed_data["data"]

    summary_parts = [f"Dataset with {parsed_data['rows']} rows and {len(columns)} columns:"]
    summary_parts.append(f"Columns: {', '.join(columns)}")

    # Show first few rows as examples
    if isinstance(data, list) and len(data) > 0:
        summary_parts.append("\nFirst few rows:")
        for i, row in enumerate(data[:5]):
            if isinstance(row, dict):
                row_str = ", ".join(f"{k}={v}" for k, v in row.items())
            else:
                row_str = str(row)
            summary_parts.append(f"  Row {i+1}: {row_str}")
        if len(data) > 5:
            summary_parts.append(f"  ... and {len(data) - 5} more rows")

    return "\n".join(summary_parts)

