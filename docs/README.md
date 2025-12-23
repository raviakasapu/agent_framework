# Documentation Server

The docs_server provides an interactive web interface for viewing agent manifests, documentation, and examples.

## Features

- **Agent Manifest Viewer**: Interactive documentation of agent tools and schemas
- **Markdown Documentation**: Browse framework documentation files
- **Example Browser**: View example scripts and agent configurations
- **API Reference**: Link to Sphinx-generated API docs (if built)

## Quick Start

### 1. Generate Agent Manifest

```bash
python generate_manifest.py \
  --config configs/agents/chat_assistant.yaml \
  --output docs/agent_manifest.json
```

### 2. Start Documentation Server

```bash
# Default (uses docs/agent_manifest.json)
uvicorn docs_server.main:app --reload --port 8000

# Custom manifest path
AGENT_MANIFEST_PATH=docs/my_manifest.json uvicorn docs_server.main:app --reload --port 8000
```

### 3. Open Browser

Visit http://localhost:8000

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AGENT_MANIFEST_PATH` | Path to agent manifest JSON | `agent_manifest.json` |
| `AGENT_DOCS_DIR` | Path to Sphinx HTML docs | `docs/sphinx/build/html` |
| `AGENT_EXAMPLES_DIR` | Path to example scripts | `examples` |
| `AGENT_CONFIGS_DIR` | Path to agent configs | `configs/agents` |

## Available Routes

### `/` - Agent Manifest
Interactive documentation showing:
- Agent name, description, version
- Available tools with parameters and return types
- Expandable tool details

### `/pages` - Documentation Pages
Lists all Markdown files in the `docs/` directory:
- Framework guides
- Getting started tutorials
- API documentation

### `/page?name=<filename>` - View Page
View a specific Markdown file (rendered as plain text)

### `/examples` - Examples Browser
Lists:
- Example Python scripts
- Agent configuration YAMLs
- Click to view source code

### `/raw?base=<base>&path=<path>` - Raw File
View raw file contents (plain text)

Supported bases:
- `examples`
- `configs/agents`
- `docs`

### `/reference` - API Reference
Serves Sphinx-generated HTML documentation (if available)

## Generating Manifests

The manifest generator extracts tool schemas from agent configurations:

```bash
# For a specific agent
python generate_manifest.py \
  --config configs/agents/orchestrator.yaml \
  --output docs/orchestrator_manifest.json

# Then serve it
AGENT_MANIFEST_PATH=docs/orchestrator_manifest.json \
  uvicorn docs_server.main:app --reload
```

## Manifest Format

```json
{
  "agent_name": "MyAgent",
  "description": "Agent description",
  "version": "1.0.0",
  "tools": [
    {
      "name": "tool_name",
      "description": "Tool description",
      "parameters": {
        "param1": {
          "type": "string",
          "description": "Parameter description"
        }
      },
      "required": ["param1"],
      "returns": {
        "type": "object",
        "properties": {
          "result": {"type": "string"}
        }
      }
    }
  ]
}
```

## Use Cases

### 1. Agent Documentation
Generate and serve documentation for your custom agents:
```bash
python generate_manifest.py --config my_agent.yaml --output docs/my_agent.json
AGENT_MANIFEST_PATH=docs/my_agent.json uvicorn docs_server.main:app
```

### 2. Team Collaboration
Share agent capabilities with your team via the web interface

### 3. API Discovery
Explore available tools and their schemas interactively

### 4. Testing & Debugging
Verify tool schemas are correctly defined

## Customization

### Custom Styling
Edit the inline CSS in `docs_server/main.py` (lines 56-63)

### Additional Routes
Add new routes to the FastAPI app in `docs_server/main.py`

### Markdown Rendering
Currently uses plain text rendering. To add proper Markdown rendering:

```python
# Install markdown library
pip install markdown

# Update /page route
import markdown
html_content = markdown.markdown(text)
return HTMLResponse(f"<h1>{name}</h1>{html_content}")
```

## Integration with Main Server

The docs server is separate from the agent execution server (`tests/simple_app.py`).

**Agent Server** (port 8051):
- Executes agents
- WebSocket support
- Production API

**Docs Server** (port 8000):
- Documentation
- Examples
- Manifest viewer

Run both:
```bash
# Terminal 1: Agent server
python run_agent_app.py

# Terminal 2: Docs server
uvicorn docs_server.main:app --reload --port 8000
```

## Troubleshooting

### "Agent manifest not found"
Generate a manifest first:
```bash
python generate_manifest.py --config configs/agents/research_assistant.yaml
```

### "No Markdown files found"
The docs server looks for `*.md` files in the `docs/` directory. The framework documentation is at the SDK root level.

### Port already in use
Change the port:
```bash
uvicorn docs_server.main:app --port 8001
```

## Production Deployment

For production, consider:
1. **Static Generation**: Pre-generate HTML instead of serving dynamically
2. **Authentication**: Add API key or OAuth
3. **HTTPS**: Use reverse proxy (nginx, Caddy)
4. **Caching**: Cache manifest and file reads
5. **Rate Limiting**: Prevent abuse

Example with nginx:
```nginx
server {
    listen 80;
    server_name docs.example.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
    }
}
```

## See Also

- [FRAMEWORK_GUIDE.md](../FRAMEWORK_GUIDE.md) - Complete framework documentation
- [GETTING_STARTED.md](../GETTING_STARTED.md) - Quick start tutorial
- [README.md](../README.md) - Main README

