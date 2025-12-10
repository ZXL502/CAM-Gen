"""Export DeepCAD-like design sequences to JSON with physics and G-code."""

import json
import random
from pathlib import Path
from typing import Any, Iterable, List

from .physics_engine import CNCPhysics


def _build_demo_sketch(doc: Any) -> Any:
    """Placeholder reconstruction that builds a simple rectangular sketch."""

    FreeCAD = __import__("FreeCAD")
    Part = __import__("Part")

    sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
    sketch.addGeometry(
        Part.LineSegment(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(50, 0, 0)), False
    )
    sketch.addGeometry(
        Part.LineSegment(FreeCAD.Vector(50, 0, 0), FreeCAD.Vector(50, 50, 0)), False
    )
    sketch.addGeometry(
        Part.LineSegment(FreeCAD.Vector(50, 50, 0), FreeCAD.Vector(0, 50, 0)), False
    )
    sketch.addGeometry(
        Part.LineSegment(FreeCAD.Vector(0, 50, 0), FreeCAD.Vector(0, 0, 0)), False
    )
    return sketch


def process_deepcad_sample(sequence_data: Iterable[str], output_filename: str) -> None:
    """Rebuild geometry, inject physics, compile toolpath, and export JSON."""

    FreeCAD = __import__("FreeCAD")
    Part = __import__("Part")
    PathWorkbench = __import__("Path")
    fanuc = __import__("Path.Post.Scripts.fanuc", fromlist=["fanuc"]).post

    phy = CNCPhysics()

    doc = FreeCAD.newDocument()

    sketch = _build_demo_sketch(doc)

    pad = doc.addObject("PartDesign::Pad", "Pad")
    pad.Profile = sketch
    pad.Length = 10.0
    doc.recompute()

    mat_name = random.choice(["Alu_6061", "Steel_45"])
    tool_name = "T1_EndMill_10"
    S, F = phy.get_milling_params(mat_name, tool_name)

    job = PathWorkbench.createJob(pad)
    job.PostProcessor = "fanuc"

    tool_controller = PathWorkbench.ToolController("TC")
    tool_controller.ToolNumber = 1
    tool_controller.SpindleSpeed = S
    tool_controller.HorizFeed = F
    tool_controller.VertFeed = max(1, int(F / 2))
    job.ToolController = tool_controller

    op = PathWorkbench.createOperation("Path::OpPocket")
    op.StepOver = 40
    job.addOperation(op)

    gcode_text, _ = fanuc(job)

    dataset_entry: dict[str, Any] = {
        "input_sequence": list(sequence_data),
        "physics_context": {"material": mat_name, "tool": tool_name},
        "manufacturing_params": {"S": S, "F": F},
        "output_gcode": gcode_text,
    }

    Path(output_filename).parent.mkdir(parents=True, exist_ok=True)
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(dataset_entry, f, indent=2)

    FreeCAD.closeDocument(doc.Name)


def process_batch(samples: List[Iterable[str]], output_dir: str) -> None:
    """Convenience helper to export multiple DeepCAD samples."""

    for idx, sample in enumerate(samples, start=1):
        process_deepcad_sample(sample, str(Path(output_dir) / f"deepcad_{idx:04d}.json"))
