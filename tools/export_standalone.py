"""
生成 standalone HTML 地图（JSON 数据内嵌到 render.html）。

用法：python export_standalone.py <algorithm-map.json>
输出：同目录下 algorithm-map.html
"""

import json
import sys
from pathlib import Path

RENDERER_HTML = Path(__file__).resolve().parent.parent / "renderer" / "render.html"


def export(json_path: str) -> str:
    json_path = Path(json_path).resolve()
    if not json_path.exists():
        print(f"Error: {json_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(RENDERER_HTML, "r", encoding="utf-8") as f:
        html = f.read()

    inject = f"<script>window.__MAP_DATA__ = {json.dumps(data, ensure_ascii=False)};</script>\n"
    html = html.replace("</head>", inject + "</head>", 1)

    out_path = json_path.with_suffix(".html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    return str(out_path)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <algorithm-map.json>")
        sys.exit(1)
    out = export(sys.argv[1])
    print(out)
