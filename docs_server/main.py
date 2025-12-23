from __future__ import annotations

import json
import os
from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse, PlainTextResponse
    from fastapi.staticfiles import StaticFiles
except Exception:  # FastAPI may not be installed in restricted envs
    FastAPI = None  # type: ignore
    HTMLResponse = None  # type: ignore


def build_app():
    if FastAPI is None:
        raise RuntimeError("FastAPI is not installed. Install with 'pip install fastapi uvicorn'.")

    app = FastAPI(
        title="Agent Framework Documentation",
        description="Interactive documentation for configured AI Agents.",
    )

    AGENT_MANIFEST_PATH = os.getenv("AGENT_MANIFEST_PATH", "agent_manifest.json")
    AGENT_DOCS_DIR = os.getenv("AGENT_DOCS_DIR", "docs/sphinx/build/html")
    EXAMPLES_DIR = os.getenv("AGENT_EXAMPLES_DIR", "examples")
    CONFIGS_DIR = os.getenv("AGENT_CONFIGS_DIR", "configs/agents")

    # Optionally mount static API reference if Sphinx has been built
    try:
        docs_path = Path(AGENT_DOCS_DIR)
        if docs_path.exists():
            app.mount("/reference", StaticFiles(directory=str(docs_path), html=True), name="reference")
    except Exception:
        pass

    @app.get("/", response_class=HTMLResponse)
    async def get_docs():
        try:
            manifest_path = Path(AGENT_MANIFEST_PATH)
            with manifest_path.open("r", encoding="utf-8") as f:
                manifest = json.load(f)
        except FileNotFoundError:
            return HTMLResponse(
                content="<h1>Error</h1><p>Agent manifest not found. Please generate one first.</p>",
                status_code=404,
            )

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset=\"utf-8\" />
            <title>Agent: {manifest.get('agent_name','Agent')}</title>
            <style>
                body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 32px; }}
                .tool {{ border: 1px solid #ddd; border-radius: 6px; margin: 16px 0; }}
                .tool-header {{ background-color: #f7f7f7; padding: 12px 16px; font-weight: 600; cursor: pointer; }}
                .tool-details {{ display: none; padding: 12px 16px; }}
                .param {{ margin-left: 16px; }}
                .required {{ color: #c00; font-weight: 700; margin-left: 4px; }}
            </style>
        </head>
        <body>
            <h1>Agent: {manifest.get('agent_name','Agent')}</h1>
            <p>{manifest.get('description','')}</p>
            <p><em>Version: {manifest.get('version','')}</em></p>
            <hr />
            <nav>
              <a href="/">Manifest</a> |
              <a href="/pages">Docs Pages</a> |
              <a href="/reference">API Reference</a> |
              <a href="/examples">Examples</a>
            </nav>
            <hr />
            <h2>Available Tools</h2>
        """

        for tool in manifest.get("tools", []):
            name = tool.get("name", "tool")
            html_content += f"""
            <div class=\"tool\">
              <div class=\"tool-header\" onclick=\"toggleDetails('{name}')\">{name}</div>
              <div id=\"{name}\" class=\"tool-details\">
                <p><strong>Description:</strong> {tool.get('description','')}</p>
                <h4>Parameters:</h4>
            """

            params = tool.get("parameters", {})
            required = set(tool.get("required", []))
            if not params:
                html_content += "<p>None</p>"
            else:
                for param_name, param in params.items():
                    is_required = param_name in required
                    required_span = '<span class="required">*</span>' if is_required else ''
                    ptype = param.get("type", param.get("anyOf", "any"))
                    desc = param.get("description", "")
                    html_content += f"""
                    <div class=\"param\">
                      <strong>{param_name}{required_span}</strong> <em>({ptype})</em>
                      <div>{desc}</div>
                    </div>
                    """

            # Render returns schema
            returns = tool.get("returns", {})
            html_content += "<h4>Returns:</h4>"
            if isinstance(returns, dict) and returns.get("properties"):
                req = set(returns.get("required", []))
                for pname, p in returns.get("properties", {}).items():
                    is_req = pname in req
                    req_span = '<span class="required">*</span>' if is_req else ''
                    ptype = p.get("type", p.get("anyOf", "any"))
                    desc = p.get("description", "")
                    html_content += f"<div class=\"param\"><strong>{pname}{req_span}</strong> <em>({ptype})</em><div>{desc}</div></div>"
            else:
                # Fallback simple type
                rtype = returns.get("type", "string") if isinstance(returns, dict) else "string"
                html_content += f"<div class=\"param\">{rtype}</div>"

            html_content += """
              </div>
            </div>
            """

        html_content += """
        <script>
          function toggleDetails(toolId) {
            var el = document.getElementById(toolId);
            if (el.style.display === 'block') { el.style.display = 'none'; } else { el.style.display = 'block'; }
          }
        </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    def _safe_under(base: Path, p: Path) -> bool:
        try:
            p.resolve().relative_to(base.resolve())
            return True
        except Exception:
            return False

    @app.get("/pages", response_class=HTMLResponse)
    async def list_pages():
        docs_dir = Path("docs")
        pages = []
        if docs_dir.exists():
            for md in docs_dir.glob("*.md"):
                pages.append(md.name)
        html = [
            "<h1>Project Docs</h1>",
            "<p>Click to view Markdown files under docs/</p>",
            "<ul>",
        ]
        for name in pages:
            html.append(f"<li><a href=\"/page?name={name}\">{name}</a></li>")
        html.append("</ul>")
        if not pages:
            html.append("<p>No Markdown files found in docs/</p>")
        return HTMLResponse("\n".join(html))

    @app.get("/page", response_class=HTMLResponse)
    async def view_page(name: str):
        docs_dir = Path("docs")
        md_path = docs_dir / name
        if not (md_path.exists() and _safe_under(docs_dir, md_path)):
            raise HTTPException(status_code=404, detail="Page not found")
        text = md_path.read_text(encoding="utf-8")
        # Very simple render: escape HTML and wrap in <pre> for now
        import html as _html
        safe = _html.escape(text)
        body = f"<h1>{name}</h1><pre>{safe}</pre>"
        return HTMLResponse(body)

    @app.get("/examples", response_class=HTMLResponse)
    async def list_examples():
        ex_dir = Path(EXAMPLES_DIR)
        cfg_dir = Path(CONFIGS_DIR)
        html = ["<h1>Examples</h1>", "<h2>Example Scripts</h2>", "<ul>"]
        if ex_dir.exists():
            for py in ex_dir.glob("**/*.py"):
                rel = py.relative_to(ex_dir)
                html.append(f"<li><a href=\"/raw?base=examples&path={rel}\">{rel}</a></li>")
        html.append("</ul><h2>Agent Configs</h2><ul>")
        if cfg_dir.exists():
            for y in cfg_dir.glob("**/*.yaml"):
                rel = y.relative_to(cfg_dir)
                html.append(f"<li><a href=\"/raw?base=configs/agents&path={rel}\">{rel}</a></li>")
        html.append("</ul>")
        return HTMLResponse("\n".join(html))

    @app.get("/raw", response_class=PlainTextResponse)
    async def raw(base: str, path: str):
        if base not in {"examples", "configs/agents", "agent_configs", "docs"}:
            raise HTTPException(status_code=400, detail="Invalid base")
        base_path = Path(base)
        file_path = (base_path / path).resolve()
        if not (_safe_under(base_path, file_path) and file_path.exists() and file_path.is_file()):
            raise HTTPException(status_code=404, detail="File not found")
        return PlainTextResponse(file_path.read_text(encoding="utf-8"))

    return app


# For `uvicorn docs_server.main:app`
app = build_app() if FastAPI is not None else None
