from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from .models import (
    AnalysisRow,
    Bounds,
    CadDocument,
    ControlPoint,
    ExtractionResult,
    Patch,
    PatchCriteria,
    PatchEvaluation,
    Section,
)
from .reasoners import VisionReasoner


class Trace:
    def __init__(self) -> None:
        self._events: list[str] = []

    def add(self, message: str) -> None:
        self._events.append(message)

    def snapshot(self) -> tuple[str, ...]:
        return tuple(self._events)


class OrchestratorAgent:
    def __init__(self, trace: Trace) -> None:
        self.trace = trace

    def split_documents(self, documents: Iterable[CadDocument]) -> tuple[tuple[CadDocument, ...], tuple[CadDocument, ...]]:
        common: list[CadDocument] = []
        drawings: list[CadDocument] = []
        for document in documents:
            if document.is_common_info or any(section.kind in {"legend", "device_table"} for section in document.sections):
                common.append(document)
            else:
                drawings.append(document)
        self.trace.add(f"orchestrator: routed {len(common)} common-info document(s), {len(drawings)} drawing document(s)")
        return tuple(common), tuple(drawings)


class CommonInfoAggregatorAgent:
    def __init__(self, trace: Trace) -> None:
        self.trace = trace

    def aggregate(self, documents: Iterable[CadDocument]) -> ExtractionResult:
        symbols: dict[str, str] = {}
        devices: dict[str, str] = {}
        for document in documents:
            for section in document.sections:
                symbols.update(section.symbols)
                devices.update(section.devices)
        self.trace.add(f"common-info-aggregator: collected {len(symbols)} symbol(s), {len(devices)} device mapping(s)")
        return ExtractionResult(symbols=symbols, devices=devices)


class ExampleAnalyzerAgent:
    def __init__(self, reasoner: VisionReasoner, trace: Trace) -> None:
        self.reasoner = reasoner
        self.trace = trace

    def analyze(self, examples: tuple[Section, ...]) -> PatchCriteria:
        criteria = self.reasoner.learn_patch_criteria(examples)
        self.trace.add(f"example-analyzer: learned {len(criteria.rules)} patch criteria")
        return criteria


class SectionSplitterAgent:
    def __init__(self, trace: Trace) -> None:
        self.trace = trace

    def split(self, document: CadDocument, criteria: PatchCriteria) -> tuple[Patch, ...]:
        patches: list[Patch] = []
        for section in document.sections:
            bounds = section.bounds
            metadata = {"criteria": criteria.rules, "source_kind": section.kind}
            kind = "blueprint"
            if section.kind == "mixed" and section.has_table:
                metadata["table_extracted_as_metadata"] = True
            patch = Patch(
                id=f"{document.id}:{section.id}:patch",
                document_id=document.id,
                section_id=section.id,
                kind=kind,
                title=section.title,
                bounds=bounds,
                metadata=metadata,
            )
            patches.append(patch)
        self.trace.add(f"section-splitter: generated {len(patches)} initial patch(es) for {document.filename}")
        return tuple(patches)


class PatchEvaluatorAgent:
    def evaluate(self, patch: Patch, section: Section) -> PatchEvaluation:
        issues: list[str] = []
        if section.title_position == "outside" and not patch.metadata.get("title_margin_added"):
            issues.append("missing_external_title")
        if section.kind == "mixed" and section.has_table and not patch.metadata.get("table_extracted_as_metadata"):
            issues.append("table_mixed_with_blueprint")
        return PatchEvaluation(passed=not issues, issues=tuple(issues))


class StrategyPlannerAgent:
    def plan(self, evaluation: PatchEvaluation) -> tuple[str, ...]:
        actions: list[str] = []
        if "missing_external_title" in evaluation.issues:
            actions.append("add_top_title_margin")
        if "table_mixed_with_blueprint" in evaluation.issues:
            actions.append("separate_table_metadata")
        return tuple(actions)


class CodeModifierAgent:
    def __init__(self, trace: Trace) -> None:
        self.trace = trace

    def apply(self, patch: Patch, actions: tuple[str, ...]) -> Patch:
        bounds = patch.bounds
        metadata = dict(patch.metadata)
        if "add_top_title_margin" in actions:
            bounds = bounds.expand(top=50)
            metadata["title_margin_added"] = True
        if "separate_table_metadata" in actions:
            metadata["table_extracted_as_metadata"] = True
        updated = replace(patch, bounds=bounds, metadata=metadata)
        self.trace.add(f"code-modifier: applied {', '.join(actions)} to {patch.id}")
        return updated


class SelfCorrectingPatchAgent:
    def __init__(self, trace: Trace) -> None:
        self.evaluator = PatchEvaluatorAgent()
        self.planner = StrategyPlannerAgent()
        self.modifier = CodeModifierAgent(trace)
        self.trace = trace

    def refine(self, patch: Patch, section: Section, max_iterations: int = 3) -> Patch:
        current = patch
        for iteration in range(1, max_iterations + 1):
            evaluation = self.evaluator.evaluate(current, section)
            if evaluation.passed:
                self.trace.add(f"patch-loop: {current.id} passed at iteration {iteration}")
                return current
            actions = self.planner.plan(evaluation)
            self.trace.add(f"patch-loop: {current.id} failed with {evaluation.issues}; planned {actions}")
            current = self.modifier.apply(current, actions)
        return current


class DxfInfoAggregatorAgent:
    def __init__(self, trace: Trace) -> None:
        self.trace = trace

    def aggregate(self, documents: Iterable[CadDocument]) -> ExtractionResult:
        points: list[ControlPoint] = []
        context: dict[str, str] = {}
        for document in documents:
            for section in document.sections:
                points.extend(section.control_points)
                for point in section.control_points:
                    if point.duct_context:
                        context[point.id] = point.duct_context
        self.trace.add(f"dxf-info-aggregator: collected {len(points)} control point(s)")
        return ExtractionResult(control_points=tuple(points), context=context)


class DetailedInfoAggregatorAgent:
    def __init__(self, reasoner: VisionReasoner, trace: Trace) -> None:
        self.reasoner = reasoner
        self.trace = trace

    def analyze(
        self,
        document: CadDocument,
        extraction: ExtractionResult,
        tacit_rules: dict[str, dict[str, str]],
    ) -> tuple[AnalysisRow, ...]:
        rows: list[AnalysisRow] = []
        section_by_point = {
            point.id: section.id
            for section in document.sections
            for point in section.control_points
        }
        for point in extraction.control_points:
            if point.id not in section_by_point:
                continue
            connected, reason = self.reasoner.infer_connected_device(point, extraction.symbols, extraction.devices)
            rule = tacit_rules.get(point.connected_symbol or "", {})
            final_device = connected
            function = rule.get(point.point_type, "unknown")
            if point.connected_symbol == "EC_FAN" and point.duct_context == "SA":
                final_device = "SF"
            if point.connected_symbol == "DM" and point.duct_context:
                final_device = {
                    "EA_BYPASS": "External By-pass Damper",
                    "EA": "External Damper",
                    "MIXED": "Mixed Damper",
                }.get(point.duct_context, connected)
                function = "control"
            rows.append(
                AnalysisRow(
                    document_id=document.id,
                    section_id=section_by_point.get(point.id, "unknown"),
                    control_point_id=point.id,
                    point_type=point.point_type,
                    connected_device=final_device,
                    function=function,
                    confidence=0.86 if function != "unknown" else 0.55,
                    rationale=f"{reason}; context={point.duct_context or 'n/a'}",
                )
            )
        self.trace.add(f"detailed-info-aggregator: produced {len(rows)} analysis row(s)")
        return tuple(rows)


def merge_extractions(*items: ExtractionResult) -> ExtractionResult:
    symbols: dict[str, str] = {}
    devices: dict[str, str] = {}
    points: list[ControlPoint] = []
    context: dict[str, str] = {}
    for item in items:
        symbols.update(item.symbols)
        devices.update(item.devices)
        points.extend(item.control_points)
        context.update(item.context)
    return ExtractionResult(symbols=symbols, devices=devices, control_points=tuple(points), context=context)
