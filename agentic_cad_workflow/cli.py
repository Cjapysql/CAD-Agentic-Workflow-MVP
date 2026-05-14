from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import Bounds, CadDocument, ControlPoint, Section
from .sample_data import sample_documents
from .workflow import run_workflow


def _load_documents(path: Path) -> tuple[CadDocument, ...]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return tuple(_document_from_dict(item) for item in raw["documents"])


def _document_from_dict(item: dict[str, Any]) -> CadDocument:
    return CadDocument(
        id=item["id"],
        filename=item["filename"],
        is_common_info=item.get("is_common_info", False),
        metadata=item.get("metadata", {}),
        sections=tuple(_section_from_dict(section) for section in item["sections"]),
    )


def _section_from_dict(item: dict[str, Any]) -> Section:
    bounds = item["bounds"]
    return Section(
        id=item["id"],
        title=item["title"],
        kind=item["kind"],
        bounds=Bounds(bounds["x"], bounds["y"], bounds["width"], bounds["height"]),
        title_position=item.get("title_position", "inside"),
        has_table=item.get("has_table", False),
        symbols=item.get("symbols", {}),
        devices=item.get("devices", {}),
        control_points=tuple(_point_from_dict(point) for point in item.get("control_points", [])),
    )


def _point_from_dict(item: dict[str, Any]) -> ControlPoint:
    return ControlPoint(
        id=item["id"],
        point_type=item["point_type"],
        label=item["label"],
        location=tuple(item["location"]),
        connected_symbol=item.get("connected_symbol"),
        duct_context=item.get("duct_context"),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the CAD Agentic Workflow prototype.")
    parser.add_argument("--input", type=Path, help="JSON file containing extracted CAD document structures.")
    parser.add_argument("--output", type=Path, help="Write workflow result JSON to this path.")
    args = parser.parse_args()

    documents = _load_documents(args.input) if args.input else sample_documents()
    result = run_workflow(documents)
    payload = asdict(result)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()

