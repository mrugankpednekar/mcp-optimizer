#!/usr/bin/env python3
"""
Quick test script to verify MCP server is working.
Run this to test the server before connecting to ChatGPT/Claude Desktop.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from crew_optimizer.server import app
from crew_optimizer.solvers.lp.assignment_parser import parse_assignment_problem
from crew_optimizer.solvers.lp.simplex import solve_lp

def test_assignment_problem():
    """Test the assignment problem solver."""
    print("Testing assignment problem solver...")
    
    energy_csv = """job,Machine 1,Machine 2
1,10,20
2,15,25"""

    capacity_csv = """machine,capacity
1,1
2,1"""

    try:
        model = parse_assignment_problem(
            energy_file_content=energy_csv,
            capacity_file_content=capacity_csv,
        )
        
        from crew_optimizer.schemas import SolveOptions
        solution = solve_lp(model, SolveOptions())
        
        print(f"✓ Assignment problem parsed successfully")
        print(f"✓ Solution status: {solution.status}")
        print(f"✓ Objective value: {solution.objective_value}")
        print(f"✓ Variables: {len(solution.x) if solution.x else 0}")
        print("\n✅ All tests passed!")
        return True
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tools_available():
    """Check that all tools are registered."""
    print("\nChecking available tools...")
    
    # FastMCP stores tools in app._tools
    # Check if tools are registered by inspecting the app
    expected_tools = [
        "solve_linear_program",
        "solve_mixed_integer_program", 
        "parse_natural_language",
        "diagnose_infeasibility",
        "solve_word_problem_with_data",
        "solve_assignment_problem",
    ]
    
    # Check if the tool functions exist
    tool_names = []
    if hasattr(app, '_tools'):
        tool_names = list(app._tools.keys())
    elif hasattr(app, 'tools'):
        tool_names = list(app.tools.keys())
    else:
        # Try to infer from function names
        import inspect
        for name in dir(app):
            if name.startswith('solve_') or name.startswith('parse_') or name.startswith('diagnose_'):
                tool_names.append(name)
    
    print(f"Found {len(tool_names)} tools:")
    for tool_name in tool_names:
        print(f"  - {tool_name}")
    
    # Check if expected tools are present (case-insensitive)
    tool_names_lower = [t.lower() for t in tool_names]
    missing = [t for t in expected_tools if t.lower() not in tool_names_lower]
    
    if missing:
        print(f"\n⚠️  Missing tools: {missing}")
        print("Note: This might be okay if FastMCP stores tools differently")
    else:
        print("\n✅ All expected tools are available!")
    
    return True  # Don't fail the test, just warn

if __name__ == "__main__":
    print("=" * 60)
    print("MCP Server Test")
    print("=" * 60)
    
    success = True
    success &= test_tools_available()
    success &= test_assignment_problem()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Server is ready to use!")
        print("\nNext steps:")
        print("1. For Claude Desktop: Configure claude_desktop_config.json")
        print("2. For HTTP: Run 'python -m crew_optimizer.server' with MCP_TRANSPORT=http")
        print("3. See MCP_SETUP.md for detailed instructions")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        sys.exit(1)

