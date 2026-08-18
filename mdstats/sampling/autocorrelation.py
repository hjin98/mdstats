"""Source-independent autocorrelation estimation for correlated trajectories.

The initial implementation is deliberately narrow and deterministic.  It uses
an FFT-computed unbiased autocovariance followed by Geyer's initial-positive-
sequence truncation.  The exact policy is serialized because block sizes and
all downstream effective-sample diagnostics depend on it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

import numpy as np

from ._common import (
    SamplingInputError,
    SamplingSerializationError,
    digest,
    finite_float,
)

AUTOCORRELATION_POLICY_SCHEMA = "mdstats.sampling-autocorrelation-policy.v1"
AUTOCORRELATION_ESTIMATE_SCHEMA = "mdstats.sampling-autocorrelation-estimate.v1"
AUTOCORRELATION_POLICY_VERSION = (
    "mdstats.sampling-autocorrelation.initial-positive-sequence.2026-07.v1"
)


class AutocorrelationEstimateStatus(str, Enum):
    """Evidence state for one one-dimensional autocorrelation estimate."""

    ESTIMATED = "estimated"
    CONSTANT = "constant"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True, slots=True)
class AutocorrelationPolicy:
    """Immutable numerical contract for integrated autocorrelation time.

    ``minimum_tau_frames=0.5`` follows the convention

    ``tau = 1/2 + sum_{k>0} rho(k)``.

    With this convention an uncorrelated sequence has ``tau=0.5`` and effective
    sample count ``N / (2 tau) = N``.
    """

    policy_version: str = AUTOCORRELATION_POLICY_VERSION
    estimator: str = "fft_unbiased_initial_positive_sequence"
    minimum_observations: int = 3
    minimum_tau_frames: float = 0.5
    maximum_tau_fraction: float = 0.5
    variance_floor: float = float(np.finfo(np.float64).eps)

    def __post_init__(self) -> None:
        if not self.policy_version:
            raise SamplingInputError("Autocorrelation policy version is required.")
        if self.estimator != "fft_unbiased_initial_positive_sequence":
            raise SamplingInputError("Unsupported autocorrelation estimator.")
        if self.minimum_observations < 1:
            raise SamplingInputError("minimum_observations must be positive.")
        minimum_tau = finite_float(self.minimum_tau_frames, name="minimum_tau_frames")
        maximum_fraction = finite_float(
            self.maximum_tau_fraction, name="maximum_tau_fraction"
        )
        variance_floor = finite_float(self.variance_floor, name="variance_floor")
        if minimum_tau <= 0.0:
            raise SamplingInputError("minimum_tau_frames must be positive.")
        if not 0.0 < maximum_fraction <= 1.0:
            raise SamplingInputError("maximum_tau_fraction must lie in (0, 1].")
        if variance_floor < 0.0:
            raise SamplingInputError("variance_floor must be nonnegative.")
        if minimum_tau > maximum_fraction * self.minimum_observations:
            raise SamplingInputError(
                "minimum_tau_frames is incompatible with maximum_tau_fraction "
                "at minimum_observations."
            )
        object.__setattr__(self, "minimum_tau_frames", minimum_tau)
        object.__setattr__(self, "maximum_tau_fraction", maximum_fraction)
        object.__setattr__(self, "variance_floor", variance_floor)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": AUTOCORRELATION_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "estimator": self.estimator,
            "minimum_observations": self.minimum_observations,
            "minimum_tau_frames": self.minimum_tau_frames,
            "maximum_tau_fraction": self.maximum_tau_fraction,
            "variance_floor": self.variance_floor,
        }

    @property
    def signature(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AutocorrelationPolicy":
        if payload.get("schema") != AUTOCORRELATION_POLICY_SCHEMA:
            raise SamplingSerializationError(
                "Unsupported sampling-autocorrelation-policy schema."
            )
        result = cls(
            policy_version=str(payload["policy_version"]),
            estimator=str(payload["estimator"]),
            minimum_observations=int(payload["minimum_observations"]),
            minimum_tau_frames=float(payload["minimum_tau_frames"]),
            maximum_tau_fraction=float(payload["maximum_tau_fraction"]),
            variance_floor=float(payload["variance_floor"]),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SamplingSerializationError(
                "Sampling-autocorrelation-policy signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class AutocorrelationEstimate:
    """Signed estimate for one finite scalar sequence."""

    policy_signature: str
    status: AutocorrelationEstimateStatus
    observation_count: int
    mean: float
    variance: float
    autocorrelation_time_frames: float
    effective_sample_count: float
    truncation_lag: int
    included_positive_sequence_terms: int
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len(self.policy_signature) != 64:
            raise SamplingInputError("policy_signature must be a SHA-256 digest.")
        object.__setattr__(
            self, "status", AutocorrelationEstimateStatus(self.status)
        )
        if self.observation_count < 1:
            raise SamplingInputError("observation_count must be positive.")
        mean = finite_float(self.mean, name="mean")
        variance = finite_float(self.variance, name="variance")
        tau = finite_float(
            self.autocorrelation_time_frames,
            name="autocorrelation_time_frames",
        )
        effective = finite_float(
            self.effective_sample_count, name="effective_sample_count"
        )
        if variance < 0.0:
            raise SamplingInputError("variance must be nonnegative.")
        if tau <= 0.0:
            raise SamplingInputError(
                "autocorrelation_time_frames must be positive."
            )
        if not 0.0 <= effective <= self.observation_count + 1.0e-12:
            raise SamplingInputError("effective_sample_count is out of bounds.")
        if not 0 <= self.truncation_lag < self.observation_count:
            raise SamplingInputError("truncation_lag is out of bounds.")
        if self.included_positive_sequence_terms < 0:
            raise SamplingInputError(
                "included_positive_sequence_terms must be nonnegative."
            )
        object.__setattr__(self, "mean", mean)
        object.__setattr__(self, "variance", variance)
        object.__setattr__(self, "autocorrelation_time_frames", tau)
        object.__setattr__(self, "effective_sample_count", effective)
        object.__setattr__(self, "notes", tuple(str(value) for value in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": AUTOCORRELATION_ESTIMATE_SCHEMA,
            "policy_signature": self.policy_signature,
            "status": self.status.value,
            "observation_count": self.observation_count,
            "mean": self.mean,
            "variance": self.variance,
            "autocorrelation_time_frames": self.autocorrelation_time_frames,
            "effective_sample_count": self.effective_sample_count,
            "truncation_lag": self.truncation_lag,
            "included_positive_sequence_terms": self.included_positive_sequence_terms,
            "notes": list(self.notes),
        }

    @property
    def signature(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AutocorrelationEstimate":
        if payload.get("schema") != AUTOCORRELATION_ESTIMATE_SCHEMA:
            raise SamplingSerializationError(
                "Unsupported sampling-autocorrelation-estimate schema."
            )
        result = cls(
            policy_signature=str(payload["policy_signature"]),
            status=AutocorrelationEstimateStatus(payload["status"]),
            observation_count=int(payload["observation_count"]),
            mean=float(payload["mean"]),
            variance=float(payload["variance"]),
            autocorrelation_time_frames=float(
                payload["autocorrelation_time_frames"]
            ),
            effective_sample_count=float(payload["effective_sample_count"]),
            truncation_lag=int(payload["truncation_lag"]),
            included_positive_sequence_terms=int(
                payload["included_positive_sequence_terms"]
            ),
            notes=tuple(str(value) for value in payload.get("notes", ())),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SamplingSerializationError(
                "Sampling-autocorrelation-estimate signature mismatch."
            )
        return result


def _validated_vector(values: Sequence[float] | np.ndarray) -> np.ndarray:
    vector = np.asarray(values, dtype=np.float64)
    if vector.ndim != 1:
        raise SamplingInputError("Autocorrelation input must be one-dimensional.")
    if vector.size < 1:
        raise SamplingInputError("Autocorrelation input must be nonempty.")
    if np.any(~np.isfinite(vector)):
        raise SamplingInputError("Autocorrelation input must be finite.")
    return vector


def estimate_autocorrelation(
    values: Sequence[float] | np.ndarray,
    *,
    policy: AutocorrelationPolicy | None = None,
) -> AutocorrelationEstimate:
    """Estimate integrated autocorrelation time with deterministic truncation.

    No autocorrelation should be computed across a temporal gap; callers split a
    trajectory into contiguous runs before calling this function.
    """

    active = AutocorrelationPolicy() if policy is None else policy
    vector = _validated_vector(values)
    n = int(vector.size)
    mean = float(np.mean(vector))
    centered = vector - mean
    variance = float(np.dot(centered, centered) / n)
    tau_floor = active.minimum_tau_frames

    if n < active.minimum_observations:
        tau = min(tau_floor, active.maximum_tau_fraction * n)
        tau = max(tau, min(tau_floor, 0.5 * n))
        effective = min(float(n), float(n) / (2.0 * tau))
        return AutocorrelationEstimate(
            policy_signature=active.signature,
            status=AutocorrelationEstimateStatus.INSUFFICIENT,
            observation_count=n,
            mean=mean,
            variance=max(0.0, variance),
            autocorrelation_time_frames=tau,
            effective_sample_count=effective,
            truncation_lag=0,
            included_positive_sequence_terms=0,
            notes=("fewer observations than the policy minimum",),
        )

    if variance <= active.variance_floor:
        tau = max(
            tau_floor,
            min(tau_floor, active.maximum_tau_fraction * n),
        )
        effective = min(float(n), float(n) / (2.0 * tau))
        return AutocorrelationEstimate(
            policy_signature=active.signature,
            status=AutocorrelationEstimateStatus.CONSTANT,
            observation_count=n,
            mean=mean,
            variance=max(0.0, variance),
            autocorrelation_time_frames=tau,
            effective_sample_count=effective,
            truncation_lag=0,
            included_positive_sequence_terms=0,
            notes=("variance is at or below the policy floor",),
        )

    fft_size = 1 << (2 * n - 1).bit_length()
    transformed = np.fft.rfft(centered, n=fft_size)
    autocovariance = np.fft.irfft(
        transformed * np.conjugate(transformed), n=fft_size
    )[:n]
    autocovariance /= np.arange(n, 0, -1, dtype=np.float64)
    rho = autocovariance / autocovariance[0]

    tau = tau_floor
    index = 1
    truncation_lag = 0
    included_terms = 0
    while index < n:
        if index + 1 < n:
            pair = float(rho[index] + rho[index + 1])
            if pair <= 0.0:
                break
            tau += pair
            truncation_lag = index + 1
            included_terms += 2
            index += 2
        else:
            if rho[index] <= 0.0:
                break
            tau += float(rho[index])
            truncation_lag = index
            included_terms += 1
            index += 1

    tau = max(
        tau_floor,
        min(float(tau), active.maximum_tau_fraction * n),
    )
    effective = min(float(n), float(n) / (2.0 * tau))
    return AutocorrelationEstimate(
        policy_signature=active.signature,
        status=AutocorrelationEstimateStatus.ESTIMATED,
        observation_count=n,
        mean=mean,
        variance=variance,
        autocorrelation_time_frames=tau,
        effective_sample_count=effective,
        truncation_lag=truncation_lag,
        included_positive_sequence_terms=included_terms,
    )


def integrated_autocorrelation_time(
    values: Sequence[float] | np.ndarray,
    *,
    policy: AutocorrelationPolicy | None = None,
) -> float:
    """Return only the integrated autocorrelation time in stored-frame units."""

    return estimate_autocorrelation(values, policy=policy).autocorrelation_time_frames


def effective_sample_count(
    observation_count: int,
    autocorrelation_time_frames: float,
) -> float:
    """Return ``min(N, N/(2 tau))`` under the mdstats tau convention."""

    if observation_count < 0:
        raise SamplingInputError("observation_count must be nonnegative.")
    if observation_count == 0:
        return 0.0
    tau = finite_float(
        autocorrelation_time_frames, name="autocorrelation_time_frames"
    )
    if tau <= 0.0:
        raise SamplingInputError(
            "autocorrelation_time_frames must be positive."
        )
    return min(float(observation_count), float(observation_count) / (2.0 * tau))
