from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class RewardWeights:
    lambda_geo: float = 0.5
    lambda_phys: float = 0.3
    lambda_eff: float = 0.2
    full_width_threshold: float = 500.0
    collision_penalty: float = -500.0


def iou(final: np.ndarray, target: np.ndarray) -> float:
    intersection = np.logical_and(final, target).sum()
    union = np.logical_or(final, target).sum()
    return float(intersection) / float(union) if union > 0 else 0.0


def preservation(final: np.ndarray, target: np.ndarray) -> float:
    target_voxels = target.sum()
    preserved = np.logical_and(final, target).sum()
    return float(preserved) / float(target_voxels) if target_voxels > 0 else 0.0


def material_removal_rate(removed_volume: float, machining_time: float) -> float:
    return float(removed_volume) / float(machining_time) if machining_time > 0 else 0.0


def physical_reward(delta_volume: float, collision: bool, weights: RewardWeights) -> float:
    if collision:
        return weights.collision_penalty
    if delta_volume > weights.full_width_threshold:
        return -100.0
    return 0.0


def total_reward(
    final: np.ndarray,
    target: np.ndarray,
    removed_volume: float,
    machining_time: float,
    last_delta_volume: float,
    collision: bool,
    weights: Optional[RewardWeights] = None,
) -> float:
    weights = weights or RewardWeights()

    r_s = preservation(final, target)
    r_f = iou(final, target)
    r_geo = 0.5 * r_s + 0.5 * r_f

    r_phys = physical_reward(last_delta_volume, collision, weights)
    r_eff = material_removal_rate(removed_volume, machining_time)

    return (
        weights.lambda_geo * r_geo
        + weights.lambda_phys * r_phys
        + weights.lambda_eff * r_eff
    )
