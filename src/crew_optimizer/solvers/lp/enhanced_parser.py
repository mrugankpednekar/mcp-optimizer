from __future__ import annotations

from typing import Any, Dict, Optional

from ...schemas import LPModel
from .data_parser import format_data_summary, parse_data_file
from .parser import parse_nl_to_lp


def parse_word_problem_with_data(
    problem_description: str,
    file_content: Optional[str] = None,
    file_format: str = "auto",
    encoding: str = "utf-8",
    is_base64: bool = False,
    data_context: Optional[Dict[str, Any]] = None,
) -> LPModel:
    """
    Parse a word problem that references data from a file.

    This function:
    1. Parses the data file if provided
    2. Incorporates the data into the problem description
    3. Uses the enhanced description to create an LP model

    Args:
        problem_description: Natural language description of the optimization problem
        file_content: Content of the data file (optional)
        file_format: Format of the file ('csv', 'json', 'excel', 'auto')
        encoding: Text encoding
        is_base64: Whether file_content is base64 encoded
        data_context: Pre-parsed data (alternative to file_content)

    Returns:
        LPModel instance
    """
    # Parse data file if provided
    parsed_data = None
    if file_content:
        parsed_data = parse_data_file(
            file_content,
            file_format=file_format,
            encoding=encoding,
            is_base64=is_base64,
        )
    elif data_context:
        parsed_data = data_context

    # Enhance problem description with data
    enhanced_description = problem_description
    if parsed_data:
        # Try to extract and substitute data values directly into the problem description
        if isinstance(parsed_data.get("data"), list) and len(parsed_data["data"]) > 0:
            data_values = parsed_data["data"]
            columns = parsed_data.get("columns", [])
            
            # Create a data substitution: replace common patterns like "data['column']" or "column from data"
            # with actual values
            enhanced_description = _substitute_data_values(
                problem_description, data_values, columns
            )
        
        # Add data context AFTER the problem description, separated clearly
        # The parser will stop at the first "subject to" section, so we can safely add data after
        # the problem description without interfering with constraint parsing
        data_summary = format_data_summary(parsed_data)
        
        # Add data values in a format that can be referenced but won't be parsed as constraints
        if isinstance(parsed_data.get("data"), list) and len(parsed_data["data"]) > 0:
            data_values = parsed_data["data"]
            columns = parsed_data.get("columns", [])

            # Create a data reference section with explicit values
            # Place it BEFORE the problem description so it's available for reference
            # but the parser will only parse the actual problem description part
            data_ref = "--- DATA REFERENCE ---\n"
            data_ref += "Use these values in your formulation:\n"
            for i, row in enumerate(data_values[:20]):  # Limit to first 20 rows
                if isinstance(row, dict):
                    # Format as key=value pairs
                    row_parts = []
                    for k, v in row.items():
                        if isinstance(v, (int, float)):
                            row_parts.append(f"{k}={v}")
                        else:
                            row_parts.append(f"{k}={v}")
                    row_str = ", ".join(row_parts)
                    data_ref += f"Row {i+1}: {row_str}\n"
            
            # Prepend data reference to the problem description
            # The parser will start from "minimize" or "maximize" and stop at end of constraints
            enhanced_description = data_ref + "\n" + enhanced_description

    # Parse the enhanced description
    return parse_nl_to_lp(enhanced_description)


def _substitute_data_values(
    description: str, data_values: list, columns: list
) -> str:
    """
    Attempt to substitute data values into the problem description.
    
    This is a simple heuristic that looks for patterns like "column_name" and
    tries to replace them with actual values from the data.
    """
    if not data_values or not isinstance(data_values[0], dict):
        return description

    result = description
    
    # For each column, try to find references and substitute with values
    for col in columns:
        # Look for patterns like "column_name", "column_name value", etc.
        # and replace with actual numeric values
        col_lower = col.lower()
        
        # If the column name appears in the description, try to add its values
        if col_lower in description.lower() or col in description:
            # Extract numeric values for this column
            values = []
            for row in data_values:
                if isinstance(row, dict) and col in row:
                    val = row[col]
                    if isinstance(val, (int, float)):
                        values.append(val)
            
            if values:
                # Add a note about the values
                if len(values) == 1:
                    result += f" (Note: {col} = {values[0]})"
                elif len(values) <= 5:
                    result += f" (Note: {col} values: {', '.join(map(str, values))})"
                else:
                    result += f" (Note: {col} has {len(values)} values, first few: {', '.join(map(str, values[:5]))})"
    
    return result

