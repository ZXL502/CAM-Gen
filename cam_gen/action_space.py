from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, List, Sequence


class Strategy(str, Enum):
    CONTOUR = "Contour"
    ZIGZAG = "Zigzag"
    TURNING_ROUGH = "Turning_Rough"
    TURNING_FINISH = "Turning_Finish"


@dataclass
class ActionVector:
    """Parameterized description of a machining step.

    Each action keeps the model output compact while still allowing deterministic
    generation of valid G-code.
    """

    tool_id: int
    strategy: Strategy
    layer_height: float
    speed_factor: float
    metadata: Dict[str, float] | None = None

    def compile_to_gcode(self, start_point: Sequence[float]) -> List[str]:
        """Translate the structured action into deterministic G-code commands.

        Args:
            start_point: XYZ starting coordinate used to anchor the emitted
                commands. This keeps the compiler stateless and easy to test.
        """

        commands: List[str] = [f"T{self.tool_id:02d}01"]
        base_feed = 1200.0  # mm/min baseline configurable per machine
        feed_rate = base_feed * self.speed_factor

        strategy_generators = {
            Strategy.CONTOUR: self._compile_contour,
            Strategy.ZIGZAG: self._compile_zigzag,
            Strategy.TURNING_ROUGH: self._compile_turning_rough,
            Strategy.TURNING_FINISH: self._compile_turning_finish,
        }
        generator = strategy_generators.get(self.strategy)
        if generator is None:
            raise ValueError(f"Unsupported strategy {self.strategy}")

        commands.extend(generator(start_point=start_point, feed_rate=feed_rate))
        return commands

    def _compile_contour(self, *, start_point: Sequence[float], feed_rate: float) -> List[str]:
        x0, y0, z0 = start_point
        depth = z0 - self.layer_height
        return [
            f"G00 X{x0:.3f} Y{y0:.3f} Z{z0:.3f}",
            f"G01 Z{depth:.3f} F{feed_rate:.1f}",
            f"G03 X{x0:.3f} Y{y0:.3f} I0.0 J0.0 F{feed_rate:.1f}",
            f"G00 Z{z0:.3f}",
        ]

    def _compile_zigzag(self, *, start_point: Sequence[float], feed_rate: float) -> List[str]:
        x0, y0, z0 = start_point
        depth = z0 - self.layer_height
        step_over = self.metadata.get("step_over", 2.0) if self.metadata else 2.0
        passes = self.metadata.get("passes", 3) if self.metadata else 3
        commands = [f"G00 X{x0:.3f} Y{y0:.3f} Z{z0:.3f}", f"G01 Z{depth:.3f} F{feed_rate:.1f}"]
        direction = 1
        for i in range(passes):
            x_target = x0 + direction * step_over
            commands.append(f"G01 X{x_target:.3f} F{feed_rate:.1f}")
            direction *= -1
        commands.append(f"G00 Z{z0:.3f}")
        return commands

    def _compile_turning_rough(self, *, start_point: Sequence[float], feed_rate: float) -> List[str]:
        x0, _, z0 = start_point
        depth = z0 - self.layer_height
        finishing_allowance = self.metadata.get("finish_allowance", 0.5) if self.metadata else 0.5
        return [
            f"G71 U{self.layer_height:.3f} W{self.layer_height:.3f} R1.0",
            f"G71 P10 Q20 U{finishing_allowance:.3f} W{finishing_allowance:.3f} F{feed_rate:.1f}",
            "N10 G00 X{:.3f} Z{:.3f}".format(x0 + self.layer_height, depth),
            "N20 G01 X{:.3f} Z{:.3f} F{:.1f}".format(x0, depth, feed_rate),
        ]

    def _compile_turning_finish(self, *, start_point: Sequence[float], feed_rate: float) -> List[str]:
        x0, _, z0 = start_point
        depth = z0 - self.layer_height
        return [
            f"G70 P10 Q20 F{feed_rate:.1f}",
            "N10 G00 X{:.3f} Z{:.3f}".format(x0, depth),
            "N20 G01 X{:.3f} Z{:.3f} F{:.1f}".format(x0, depth, feed_rate),
        ]


def compile_program(actions: Iterable[ActionVector], start_point: Sequence[float]) -> List[str]:
    """Compile a sequence of parameterized actions into G-code commands.

    The output is deterministic and ready to stream to a CNC simulator or
    training environment.
    """

    program: List[str] = ["(CAM-Gen output)"]
    point = list(start_point)
    for action in actions:
        program.extend(action.compile_to_gcode(point))
        point[2] -= action.layer_height
    program.append("M30")
    return program
