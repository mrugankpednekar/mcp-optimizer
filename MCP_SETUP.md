# MCP Server Setup Guide for ChatGPT/Claude Desktop

This guide explains how to connect the Crew Optimizer MCP server to ChatGPT or Claude Desktop.

## Option 1: Using with Claude Desktop (Recommended)

Claude Desktop has native MCP support via stdio transport.

### Step 1: Install Claude Desktop
Download and install Claude Desktop from: https://claude.ai/download

### Step 2: Configure Claude Desktop

1. Open Claude Desktop
2. Find the MCP configuration file:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

3. Edit the configuration file to add the MCP server. You can use the example file `claude_desktop_config.json.example` as a template:

```json
{
  "mcpServers": {
    "crew-optimizer": {
      "command": "python",
      "args": [
        "-m",
        "crew_optimizer.server"
      ],
      "env": {
        "PYTHONPATH": "/Users/mrugankpednekar/Documents/Optimization/project/mcp-optimizer/src"
      }
    }
  }
}
```

**Important**: 
- Update the `PYTHONPATH` to point to your actual project path
- Make sure `python` points to the Python with the virtual environment activated, or use the full path to your venv's Python: `/Users/mrugankpednekar/Documents/Optimization/project/mcp-optimizer/.venv/bin/python`

### Step 3: Restart Claude Desktop

Close and reopen Claude Desktop for the changes to take effect.

### Step 4: Test in Claude Desktop

Open Claude Desktop and try:

```
Can you help me solve an optimization problem? I have a CSV file with energy consumption data and capacity constraints.
```

Or directly:

```
Use the solve_assignment_problem tool with these files:
- energy.csv: [paste your CSV content]
- capacity.csv: [paste your CSV content]
```

## Option 2: Using with ChatGPT (HTTP Server)

ChatGPT can connect to MCP servers via HTTP. You'll need to run the server as an HTTP endpoint.

### Step 1: Start the MCP HTTP Server

```bash
cd /Users/mrugankpednekar/Documents/Optimization/project/mcp-optimizer
source .venv/bin/activate
python -m crew_optimizer.server
```

The server will start on port 8081 (or the PORT environment variable).

### Step 2: Configure ChatGPT

ChatGPT's MCP integration may vary. You'll typically need to:

1. Go to ChatGPT settings
2. Find "MCP Servers" or "Custom Tools" section
3. Add a new server with:
   - **URL**: `http://localhost:8081/mcp`
   - **Name**: `crew-optimizer`

**Note**: ChatGPT's MCP support may be limited or require specific setup. Check ChatGPT's documentation for the latest MCP integration details.

## Option 3: Using via Python Script (Direct Testing)

You can test the tools directly via Python:

```python
from crew_optimizer.server import app
from crew_optimizer.schemas import LPModel, SolveOptions

# Test the solve_assignment_problem tool
energy_csv = """job,Machine 1,Machine 2
1,10,20
2,15,25"""

capacity_csv = """machine,capacity
1,1
2,1"""

# The tools are available as app.tools
# You can call them programmatically or via the MCP protocol
```

## Option 4: Using with MCP Inspector (Testing Tool)

You can test the MCP server using the MCP Inspector:

```bash
# Install MCP Inspector
npm install -g @modelcontextprotocol/inspector

# Run the inspector
npx @modelcontextprotocol/inspector python -m crew_optimizer.server
```

This will open a web interface where you can test all the tools.

## Available Tools

Once connected, you'll have access to these tools:

1. **solve_linear_program** - Solve a linear program
2. **solve_mixed_integer_program** - Solve a mixed-integer program
3. **parse_natural_language** - Parse natural language into LP format
4. **diagnose_infeasibility** - Analyze infeasible models
5. **solve_word_problem_with_data** - Solve optimization problems with data files
6. **solve_assignment_problem** - Solve job assignment problems (NEW!)

## Example Usage in Claude Desktop

Once configured, you can ask Claude:

```
I have a cloud computing problem with 1000 jobs and 20 machines. 
I have two CSV files:
1. energy.csv - contains energy consumption for each job-machine pair
2. capacity.csv - contains capacity for each machine

Can you use the solve_assignment_problem tool to solve this?
```

Then paste your CSV files when Claude asks for them.

## Troubleshooting

### Server won't start
- Make sure you're in the virtual environment: `source .venv/bin/activate`
- Check that all dependencies are installed: `pip install -e .`
- Verify Python path is correct

### Tools not appearing in Claude Desktop
- Check the configuration file syntax (must be valid JSON)
- Ensure the PYTHONPATH points to the correct location
- Restart Claude Desktop completely
- Check Claude Desktop logs for errors

### Connection issues with HTTP server
- Verify the server is running: `curl http://localhost:8081/mcp`
- Check firewall settings
- Ensure the port (8081) is not in use by another application

## Quick Test

To quickly test if everything works:

```bash
cd /Users/mrugankpednekar/Documents/Optimization/project/mcp-optimizer
source .venv/bin/activate
python -c "from crew_optimizer.server import app; print('Server loaded successfully!')"
```

If this runs without errors, your setup is correct!

