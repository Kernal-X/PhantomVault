from __future__ import annotations

from pathlib import Path

from langgraph_pipeline import LangGraphSecurityPipeline


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    output_dir = repo_root / "cache"
    output_dir.mkdir(parents=True, exist_ok=True)

    pipeline = LangGraphSecurityPipeline()
    mermaid_text = pipeline.app.get_graph().draw_mermaid()

    mmd_path = output_dir / "langgraph_workflow.mmd"
    html_path = output_dir / "langgraph_workflow.html"

    mmd_path.write_text(mermaid_text, encoding="utf-8")

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LangGraph Workflow</title>
  <script type="module">
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
    mermaid.initialize({{
      startOnLoad: true,
      theme: "default",
      flowchart: {{ curve: "linear" }}
    }});
  </script>
  <style>
    body {{
      margin: 0;
      padding: 24px;
      font-family: Segoe UI, Arial, sans-serif;
      background: #f6f8fb;
      color: #1f2937;
    }}
    .card {{
      max-width: 1400px;
      margin: 0 auto;
      background: white;
      border-radius: 16px;
      padding: 24px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
    }}
    h1 {{
      margin-top: 0;
      font-size: 28px;
    }}
    p {{
      color: #4b5563;
    }}
    .mermaid {{
      overflow: auto;
    }}
  </style>
</head>
<body>
  <div class="card">
    <h1>LangGraph Workflow</h1>
    <p>Rendered from <code>langgraph_pipeline.py</code>.</p>
    <div class="mermaid">
{mermaid_text}
    </div>
  </div>
</body>
</html>
"""

    html_path.write_text(html, encoding="utf-8")

    print(f"Mermaid source saved to: {mmd_path}")
    print(f"Visual HTML saved to: {html_path}")
    print("Open the HTML file in a browser to view the flowchart.")


if __name__ == "__main__":
    main()
