"""Export revolve/turning design sequences to JSON with physics and template G-code."""

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List

from .physics_engine import CNCPhysics


@dataclass
class ProfilePoint:
    """Minimal profile point used for templated G71 loops."""

    x: float
    z: float
    r: float | None = None
    is_arc: bool = False


def extract_profile_points(sketch: Any) -> List[ProfilePoint]:
    """Extract profile points from a Sketcher object."""

    points: List[ProfilePoint] = []
    for edge in sketch.Geometry:  # type: ignore[attr-defined]
        if edge.TypeId == "Part::GeomArcOfCircle":
            points.append(
                ProfilePoint(
                    x=edge.EndPoint.x,
                    z=edge.EndPoint.y,
                    r=edge.Radius,
                    is_arc=True,
                )
            )
        else:
            points.append(ProfilePoint(x=edge.EndPoint.x, z=edge.EndPoint.y))
    return points


def process_revolve_sample(sequence_data: Iterable[str], output_filename: str) -> None:
    """Rebuild revolve geometry, inject physics, and export templated G71 G-code."""

    FreeCAD = __import__("FreeCAD")

    phy = CNCPhysics()

    doc = FreeCAD.newDocument()
    sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
    doc.recompute()

    revolve = doc.addObject("PartDesign::Revolution", "Revolve")
    revolve.Profile = sketch
    revolve.Angle = 360
    doc.recompute()

    mat_name = random.choice(["Alu_6061", "Steel_45"])
    Vc, F_rev = phy.get_turning_params(mat_name)

    points = extract_profile_points(sketch)

    gcode_lines = [
        "G21 G90 G40",
        f"G96 S{Vc} M03",
        "G50 S2000",
        "G00 X55.0 Z2.0",
        "G71 U2.0 R0.5",
        f"G71 P100 Q200 U0.5 W0.1 F{F_rev}",
        "N100",
    ]

    for point in points:
        if point.is_arc:
            gcode_lines.append(f"G02 X{point.x:.3f} Z{point.z:.3f} R{point.r:.3f}")
        else:
            gcode_lines.append(f"G01 X{point.x:.3f} Z{point.z:.3f}")
    gcode_lines.append("N200")

    dataset_entry = {
        "id": Path(output_filename).stem,
        "type": "turning",
        "source": "DeepCAD_Revolve",
        "input": {
            "design_tokens": list(sequence_data),
            "material": mat_name,
            "tool": "T3_Turn_Rough",
        },
        "ground_truth": {
            "gcode_text": "\n".join(gcode_lines),
            "parameters": {
                "surface_speed": Vc,
                "feed_per_rev": F_rev,
            },
        },
    }

    Path(output_filename).parent.mkdir(parents=True, exist_ok=True)
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(dataset_entry, f, indent=2)

    FreeCAD.closeDocument(doc.Name)


def process_batch(samples: List[Iterable[str]], output_dir: str) -> None:
    """Convenience helper to export multiple revolve samples."""

    for idx, sample in enumerate(samples, start=1):
        process_revolve_sample(sample, str(Path(output_dir) / f"revolve_{idx:04d}.json"))
