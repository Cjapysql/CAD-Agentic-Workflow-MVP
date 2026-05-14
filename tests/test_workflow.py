from agentic_cad_workflow.sample_data import sample_documents
from agentic_cad_workflow.workflow import run_workflow


def test_workflow_generates_analysis_rows() -> None:
    result = run_workflow(sample_documents())

    assert len(result.patches) == 1
    assert result.patches[0].metadata["title_margin_added"] is True
    assert result.patches[0].metadata["table_extracted_as_metadata"] is True
    assert len(result.rows) == 4


def test_ec_fan_tacit_rule_maps_supply_air_di_to_supply_fan_status() -> None:
    result = run_workflow(sample_documents())

    row = next(item for item in result.rows if item.control_point_id == "CP-001")
    assert row.connected_device == "SF"
    assert row.function == "status"


def test_same_damper_symbol_gets_context_specific_names() -> None:
    result = run_workflow(sample_documents())

    rows = {item.control_point_id: item for item in result.rows}
    assert rows["CP-003"].connected_device == "External By-pass Damper"
    assert rows["CP-004"].connected_device == "Mixed Damper"
