from __future__ import annotations

from .models import Bounds, CadDocument, ControlPoint, Section


TACIT_RULES = {
    "EC_FAN": {
        "DI": "status",
        "DO": "start_stop",
    },
    "FILTER": {
        "DI": "alarm",
    },
    "DM": {
        "AO": "control",
        "DI": "status",
    },
}


def sample_documents() -> tuple[CadDocument, ...]:
    common = CadDocument(
        id="common-001",
        filename="legend_and_device_table.dxf",
        is_common_info=True,
        sections=(
            Section(
                id="legend",
                title="Legend",
                kind="legend",
                bounds=Bounds(0, 0, 1200, 800),
                symbols={
                    "EC_FAN": "EC FAN",
                    "FILTER": "Filter",
                    "DM": "Damper",
                },
                devices={
                    "EC FAN": "Supply Fan",
                    "Filter": "Air Filter",
                    "Damper": "Air Damper",
                },
            ),
        ),
    )
    drawing = CadDocument(
        id="ahu-203",
        filename="ahu_203_control_diagram.dxf",
        sections=(
            Section(
                id="ahu-blueprint",
                title="AHU-203",
                kind="mixed",
                bounds=Bounds(100, 100, 1800, 1200),
                title_position="outside",
                has_table=True,
                control_points=(
                    ControlPoint(
                        id="CP-001",
                        point_type="DI",
                        label="DI",
                        location=(420, 530),
                        connected_symbol="EC_FAN",
                        duct_context="SA",
                    ),
                    ControlPoint(
                        id="CP-002",
                        point_type="DI",
                        label="AL",
                        location=(760, 590),
                        connected_symbol="FILTER",
                        duct_context="SA",
                    ),
                    ControlPoint(
                        id="CP-003",
                        point_type="AO",
                        label="AO",
                        location=(980, 410),
                        connected_symbol="DM",
                        duct_context="EA_BYPASS",
                    ),
                    ControlPoint(
                        id="CP-004",
                        point_type="AO",
                        label="AO",
                        location=(1020, 680),
                        connected_symbol="DM",
                        duct_context="MIXED",
                    ),
                ),
            ),
        ),
    )
    return common, drawing

