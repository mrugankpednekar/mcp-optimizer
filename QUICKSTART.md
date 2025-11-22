# Quick Start Guide: Using Crew Optimizer with ChatGPT/Claude Desktop

## 🚀 Fastest Way: Claude Desktop (Recommended)

### Step 1: Test the Server
```bash
cd /Users/mrugankpednekar/Documents/Optimization/project/mcp-optimizer
source .venv/bin/activate
python test_mcp.py
```

If you see "✅ Server is ready to use!", you're good to go!

### Step 2: Configure Claude Desktop

1. **Find your Claude Desktop config file:**
   ```bash
   # macOS
   open ~/Library/Application\ Support/Claude/claude_desktop_config.json
   
   # Or create it if it doesn't exist:
   mkdir -p ~/Library/Application\ Support/Claude
   ```

2. **Copy the example config:**
   ```bash
   cp claude_desktop_config.json.example ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

3. **Edit the config file** and update the paths to match your system:
   - Update `command` to point to your Python executable
   - Update `PYTHONPATH` to point to your project's `src` directory

4. **Restart Claude Desktop**

### Step 3: Test in Claude Desktop

Open Claude Desktop and try:

```
I have a cloud computing optimization problem. I need to assign 1000 jobs to 20 machines 
to minimize energy consumption. I have two CSV files:
- energy.csv with job-machine energy consumption
- capacity.csv with machine capacities

Can you use the solve_assignment_problem tool to solve this?
```

Then paste your CSV files when Claude asks for them.

## 🔧 Alternative: HTTP Server (for ChatGPT or other clients)

### Start the HTTP Server:
```bash
cd /Users/mrugankpednekar/Documents/Optimization/project/mcp-optimizer
source .venv/bin/activate
MCP_TRANSPORT=http python -m crew_optimizer.server
```

The server will start on `http://localhost:8081/mcp`

### Connect ChatGPT:
1. Go to ChatGPT settings
2. Find "MCP Servers" or "Custom Tools"
3. Add server URL: `http://localhost:8081/mcp`

**Note**: ChatGPT's MCP support may vary. Claude Desktop is recommended for the best experience.

## 📝 Example Usage

### Example 1: Assignment Problem
```
Use solve_assignment_problem with:
- energy_file_content: [paste your energy.csv]
- capacity_file_content: [paste your capacity.csv]
```

### Example 2: Word Problem with Data
```
Use solve_word_problem_with_data with:
- problem_description: "Minimize total cost subject to capacity constraints"
- file_content: [paste your data CSV]
```

## 🐛 Troubleshooting

### Server won't start
```bash
# Make sure you're in the venv
source .venv/bin/activate

# Check Python path
which python

# Test the server
python test_mcp.py
```

### Tools not appearing in Claude Desktop
1. Check the config file is valid JSON
2. Verify Python path is correct (use full path to venv Python)
3. Check Claude Desktop logs: `~/Library/Logs/Claude/`
4. Restart Claude Desktop completely

### Need help?
- Check `MCP_SETUP.md` for detailed instructions
- Run `python test_mcp.py` to verify setup
- Check server logs for errors

## ✅ Verification

Run this to verify everything works:
```bash
python test_mcp.py
```

You should see:
- ✅ All expected tools are available
- ✅ Assignment problem parsed successfully
- ✅ Server is ready to use!

