from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


PointType = Literal["AI", "AO", "DI", "DO"]


@dataclass(frozen=True)
class Bounds:
    x: float
    y: float
    width: float
    height: float

    def expand(self, top: float = 0, right: float = 0, bottom: float = 0, left: float = 0) -> "Bounds":
        return Bounds(
            x=self.x - left,
            y=self.y - top,
            width=self.width + left + right,
            height=self.height + top + bottom,
        )


@dataclass(frozen=True)
class ControlPoint:
    id: str
    point_type: PointType
    label: str
    location: tuple[float, float]
    connected_symbol: str | None = None
    duct_context: str | None = None


@dataclass(frozen=True)
class Section:
    id: str
    title: str
    kind: Literal["blueprint", "legend", "device_table", "mixed"]
    bounds: Bounds
    title_position: Literal["inside", "outside"] = "inside"
    has_table: bool = False
    control_points: tuple[ControlPoint, ...] = ()
    symbols: dict[str, str] = field(default_factory=dict)
    devices: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CadDocument:
    id: str
    filename: str
    sections: tuple[Section, ...]
    is_common_info: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PatchCriteria:
    rules: tuple[str, ...]


@dataclass(frozen=True)
class Patch:
    id: str
    document_id: str
    section_id: str
    kind: str
    title: str
    bounds: Bounds
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PatchEvaluation:
    passed: bool
    issues: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtractionResult:
    symbols: dict[str, str] = field(default_factory=dict)
    devices: dict[str, str] = field(default_factory=dict)
    control_points: tuple[ControlPoint, ...] = ()
    context: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class AnalysisRow:
    document_id: str
    section_id: str
    control_point_id: str
    point_type: PointType
    connected_device: str
    function: str
    confidence: float
    rationale: str


@dataclass(frozen=True)
class WorkflowResult:
    patches: tuple[Patch, ...]
    extracted: ExtractionResult
    rows: tuple[AnalysisRow, ...]
    trace: tuple[str, ...]

