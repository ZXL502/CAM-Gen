"""Simple physics helpers for calculating cutting parameters."""

import math
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class Material:
    """Material properties relevant to spindle and feed calculations."""

    Vc: float  # cutting speed (m/min)
    type: str


@dataclass(frozen=True)
class Tool:
    """Basic tool definition used for feed/speed lookup."""

    D: float  # diameter (mm)
    flutes: int | None = None
    Fz: float | None = None  # feed per tooth (mm)
    F_rev: float | None = None  # feed per revolution for turning (mm/rev)


class CNCPhysics:
    """Physics helper that computes feed and spindle targets for milling/turning."""

    def __init__(self) -> None:
        self.materials: Dict[str, Material] = {
            "Alu_6061": Material(Vc=300, type="soft"),
            "Steel_45": Material(Vc=60, type="hard"),
        }
        self.tools: Dict[str, Tool] = {
            "T1_EndMill_10": Tool(D=10.0, flutes=4, Fz=0.05),
            "T2_EndMill_4": Tool(D=4.0, flutes=2, Fz=0.02),
            # Revolve 专用车刀
            "T3_Turn_Rough": Tool(D=0, F_rev=0.25),
        }

    def get_milling_params(self, mat_name: str, tool_name: str) -> Tuple[int, int]:
        """计算铣削参数 (用于 DeepCAD 数据)."""

        mat = self.materials[mat_name]
        tool = self.tools[tool_name]

        rpm = int((mat.Vc * 1000) / (math.pi * tool.D))
        rpm = min(rpm, 12000)

        feed = int(rpm * (tool.flutes or 0) * (tool.Fz or 0.0))

        return rpm, feed

    def get_turning_params(self, mat_name: str) -> Tuple[float, float]:
        """计算车削参数 (用于 Revolve 数据)."""

        mat = self.materials[mat_name]
        return mat.Vc, self.tools["T3_Turn_Rough"].F_rev or 0.25
