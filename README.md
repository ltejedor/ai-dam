# Proof of Work LLM System

This repository demonstrates an LLM-driven development workflow using the `smolagents` library. 

## Repository Structure

- `01/` Agent Orchestrator
  - `main.py`: Interactive LLM agent that generates code files based on user prompts.
  - `proof_of_work.py`: Utilities to extract and save all tool call steps to JSON.
  - `output/`: Proof-of-work logs (`*.json`) recording every agent tool call and file operation.

## Getting Started

### Prerequisites
- Python 3.8 or newer
- pip

### Installation
Install required Python packages:
```bash
pip install smolagents requests python-dotenv markdownify
```
> Optionally, install additional libs for visualization in `02/`:
> ```bash
> pip install pandas plotly
> ```

Create a `.env` file in `01/` (if using hosted LLMs) to set API keys:
```dotenv
ANTHROPIC_API_KEY=your_anthropic_api_key
# OPENAI_API_KEY=your_openai_api_key
```

### Running the Agent
```bash
cd 01
python main.py
```
Enter tasks at the prompt. As the agent executes, you will see JSON-formatted lines printed in real time describing each step (tasks, actions, tool calls, observations, and final answers). When you exit, a complete provenance JSON file will be saved in `01/output/`.

### Exploring the Generated System
After running the agent, navigate to the `02/` folder (the generated output) and run:
```bash
python example_usage.py
```
This will execute example tools with tracking enabled and print usage statistics.

## Proof of Work
All agent actions—tool invocations and file creations—are logged in the JSON files under `01/output/`. Inspect these logs to verify how the system was built step by step.

## Building a Knowledge Graph
You can convert a proof-of-work JSON into a knowledge graph by running:
```bash
# Default: GEXF format (Gephi, Cytoscape, etc.)
python build_knowledge_graph.py output/proof_of_work_<timestamp>.json

# Or specify GraphML:
python build_knowledge_graph.py -f graphml output/proof_of_work_<timestamp>.json

# Or export as JSON (node-link data):
python build_knowledge_graph.py -f json output/proof_of_work_<timestamp>.json
```
The script requires `networkx` (install with `pip install networkx`).
Supported formats:
- GEXF (.gexf) — default, for Gephi, Cytoscape
- GraphML (.graphml) — alternative XML format
- JSON (.json) — NetworkX node-link data
You can also omit `-f` and set the desired extension in `-o`:
```bash
python build_knowledge_graph.py -o mygraph.graphml output/proof_of_work_<timestamp>.json
```  
Then load the output in your graph tool of choice or in Python with NetworkX.

## Interactive Web View
For an in-browser interactive view (pan/zoom, click nodes), use `viz_knowledge_graph.py`:
```bash
# Install dependencies:
pip install networkx pyvis

# Generate HTML (default name matches JSON basename):
python viz_knowledge_graph.py output/proof_of_work_<timestamp>.json

# Options:
# -o custom.html    # specify output file
# --title "My KG"  # add a header title
```
Open the resulting `.html` file in your browser for a fully interactive graph display.
