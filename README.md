# CAM-Gen

Reference code for a parameterized G-code generation pipeline inspired by Shape2GCode and CNC-Net.

## Structure
- `cam_gen/action_space.py`: Defines the discrete/continuous parameter vector and deterministic compiler that emits valid G-code.
- `cam_gen/simulator.py`: Implements voxel and 2D revolve subtractive simulation to approximate tool/material interaction.
- `cam_gen/rewards.py`: Computes geometry, physical safety, and efficiency rewards for reinforcement learning.
- `cam_gen/physics_engine.py`: Calculates feed/spindle targets from materials and tool libraries.
- `cam_gen/deepcad_exporter.py`: Rebuilds milling solids from design tokens, injects physics, and exports JSON with Fanuc-style G-code.
- `cam_gen/revolve_exporter.py`: Rebuilds turning shapes, injects physics, and emits templated G71 G-code plus metadata.

## Quick start
```python
from cam_gen import ActionVector, Strategy, VoxelSimulator, compile_program, total_reward
import numpy as np

actions = [
    ActionVector(tool_id=1, strategy=Strategy.TURNING_ROUGH, layer_height=2.0, speed_factor=1.0),
    ActionVector(tool_id=1, strategy=Strategy.TURNING_FINISH, layer_height=0.5, speed_factor=0.8),
]

program = compile_program(actions, start_point=(0.0, 0.0, 0.0))
print("\n".join(program))

sim = VoxelSimulator(resolution=64)
toolpath = [(0.0, 0.0, 0.0), (0.0, 0.0, -2.0), (0.0, 0.0, -4.0)]
result = sim.simulate_toolpath(toolpath, tool_radius=2.0)

# dummy target for reward demonstration
target = np.ones_like(result.remaining)
reward = total_reward(
    final=result.remaining,
    target=target,
    removed_volume=result.removed_volume,
    machining_time=10.0,
    last_delta_volume=result.removed_volume,
    collision=result.collision,
)
print("Reward:", reward)
```
