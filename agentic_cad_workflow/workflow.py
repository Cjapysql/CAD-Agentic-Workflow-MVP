from __future__ import annotations

from .agents import (
    CommonInfoAggregatorAgent,
    DetailedInfoAggregatorAgent,
    DxfInfoAggregatorAgent,
    ExampleAnalyzerAgent,
    OrchestratorAgent,
    SectionSplitterAgent,
    SelfCorrectingPatchAgent,
    Trace,
    merge_extractions,
)
from .models import CadDocument, Patch, WorkflowResult
from .reasoners import MockVisionReasoner, VisionReasoner
from .sample_data import TACIT_RULES


def run_workflow(
    documents: tuple[CadDocument, ...],
    reasoner: VisionReasoner | None = None,
    tacit_rules: dict[str, dict[str, str]] | None = None,
) -> WorkflowResult:
    trace = Trace()
    model = reasoner or MockVisionReasoner()
    rules = tacit_rules or TACIT_RULES

    orchestrator = OrchestratorAgent(trace)
    common_docs, drawing_docs = orchestrator.split_documents(documents)

    common_info = CommonInfoAggregatorAgent(trace).aggregate(common_docs)
    criteria = ExampleAnalyzerAgent(model, trace).analyze(tuple(section for doc in documents for section in doc.sections))

    splitter = SectionSplitterAgent(trace)
    patcher = SelfCorrectingPatchAgent(trace)
    patches: list[Patch] = []
    for document in drawing_docs:
        initial = splitter.split(document, criteria)
        sections = {section.id: section for section in document.sections}
        for patch in initial:
            patches.append(patcher.refine(patch, sections[patch.section_id]))

    drawing_info = DxfInfoAggregatorAgent(trace).aggregate(drawing_docs)
    extracted = merge_extractions(common_info, drawing_info)

    rows = []
    detailed = DetailedInfoAggregatorAgent(model, trace)
    for document in drawing_docs:
        rows.extend(detailed.analyze(document, extracted, rules))

    return WorkflowResult(patches=tuple(patches), extracted=extracted, rows=tuple(rows), trace=trace.snapshot())

