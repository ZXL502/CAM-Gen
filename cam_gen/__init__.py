"""Reference implementation of parameterized G-code generation and rewards."""

from .action_space import ActionVector, Strategy, compile_program
from .deepcad_exporter import process_batch as export_deepcad_batch, process_deepcad_sample
from .revolve_exporter import process_batch as export_revolve_batch, process_revolve_sample
from .rewards import RewardWeights, iou, material_removal_rate, preservation, total_reward
from .simulator import SimulationResult, VoxelSimulator

__all__ = [
    "ActionVector",
    "Strategy",
    "compile_program",
    "export_deepcad_batch",
    "process_deepcad_sample",
    "export_revolve_batch",
    "process_revolve_sample",
    "RewardWeights",
    "iou",
    "material_removal_rate",
    "preservation",
    "total_reward",
    "SimulationResult",
    "VoxelSimulator",
]
