from __future__ import annotations

from typing import Protocol

from .models import ControlPoint, PatchCriteria, Section


class VisionReasoner(Protocol):
    """Boundary for VLM/LLM calls such as Amazon Bedrock Converse."""

    def learn_patch_criteria(self, examples: tuple[Section, ...]) -> PatchCriteria:
        ...

    def infer_connected_device(
        self,
        point: ControlPoint,
        symbol_catalog: dict[str, str],
        device_catalog: dict[str, str],
    ) -> tuple[str, str]:
        ...


class MockVisionReasoner:
    """Deterministic substitute for a multimodal model during local development."""

    def learn_patch_criteria(self, examples: tuple[Section, ...]) -> PatchCriteria:
        return PatchCriteria(
            rules=(
                "section title must be included",
                "all elements belonging to the section must be included",
                "neighboring sections must be excluded",
                "mixed tables should be split into metadata when blueprint analysis is required",
                "each patch should represent one logical unit",
            )
        )

    def infer_connected_device(
        self,
        point: ControlPoint,
        symbol_catalog: dict[str, str],
        device_catalog: dict[str, str],
    ) -> tuple[str, str]:
        symbol_name = symbol_catalog.get(point.connected_symbol or "", point.connected_symbol or "unknown")
        if symbol_name in device_catalog:
            return device_catalog[symbol_name], f"symbol catalog maps {point.connected_symbol} to {symbol_name}"
        return symbol_name, f"direct symbol match for {point.connected_symbol or 'unknown'}"

