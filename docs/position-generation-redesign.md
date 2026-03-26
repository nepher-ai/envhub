# Position Generation Redesign

> **Status**: Proposal  
> **Date**: 2026-03-26  
> **Scope**: `envhub/nepher/env_cfgs/navigation/`, `envhub/environments/`, utilities

---

## 1. Problem Statement

Position generation (spawn + goal) is currently owned by **EnvCfg classes** inside
`nepher/env_cfgs/navigation/`. Each concrete config class
(`PresetNavigationEnvCfg`, `UsdNavigationEnvCfg`) embeds its own sampling
algorithms, free-zone finders, and fallback coordinate ranges. Environment
bundles that need custom logic (e.g. `obstacle-terrain-v1`) are forced to
subclass a config, override `gen_bot_pos` / `gen_goal_pos`, and fight inherited
behaviour they never use.

### What's wrong today

| Issue | Where it hurts |
|-------|---------------|
| **Sampling logic lives in config classes.** `PresetNavigationEnvCfg` has 200+ lines of free-zone computation, zone caching, and vectorized sampling that is purely numerical, not configuration. | DRY violation, hard to test in isolation. |
| **Environments can't define their own strategy without subclassing a config.** `ObstacleTerrainPresetCfg` inherits `PresetNavigationEnvCfg` only to override every spawn method and zero-out `obstacles`. The parent's free-zone path is dead code. | Fragile inheritance, wasted computation, misleading type hierarchy. |
| **Three separate, incompatible patterns** exist: free-zone rectangles (Preset), grid/occupancy sampler (USD), and pre-baked JSON pairs (obstacle-terrain-v1). There is no shared abstraction beneath `gen_goal_pos`. | No code reuse, no composability. |
| **`min_start_goal_dist` / `max_start_goal_dist` are declared on the abstract base but not enforced** by `PresetNavigationEnvCfg` (independent sampling) and only partially by `UsdNavigationEnvCfg` (only when `robot_positions` is passed). | Semantic gap — the field promises something it doesn't deliver. |
| **`validate_positions` in Preset is O(N × M) Python loops** over positions × obstacles — not vectorized, not GPU-friendly. | Perf bottleneck at scale. |
| **Unused fields accumulate.** `robot_init_pos_x_range`, `robot_init_pos_y_range` in `ObstacleTerrainPresetCfg` are explicitly unused but still inherited. `SpawnAreaConfig.allow_robot_spawn` / `allow_goal_spawn` are never consulted by `FastSpawnSampler`. | Confusing API surface. |

---

## 2. Design Goals

1. **Environments own their numerical position logic.** Each environment
   bundle defines *how* positions are generated (algorithm, data, constraints).
   This is the environment's domain knowledge.

2. **EnvCfgs become thin adapters for real-world deployment.** They translate
   environment-provided positions into Isaac Lab coordinates (env_origins,
   device placement, terrain offsets). They may add real-world constraints
   (occupancy maps from SLAM, sensor-based exclusion zones).

3. **A single, composable `PositionStrategy` protocol** replaces the three
   ad-hoc patterns with a pluggable interface.

4. **Lean core, no niche utilities.** EnvHub ships only genuinely reusable
   building blocks (occupancy sampler, uniform box, prebaked pairs). Niche
   algorithms like the free-zone rectangle finder are removed — if an
   environment needs custom geometry logic, it implements its own strategy.

5. **Testable in isolation**: strategies can be unit-tested with plain
   tensors — no Isaac Lab, no simulation, no `@configclass`.

---

## 3. Proposed Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Environment Bundle (e.g. obstacle-terrain-v1)          │
│                                                         │
│  ┌───────────────────────────────────────────┐          │
│  │ PositionStrategy  (implements protocol)   │          │
│  │  - gen_spawn(env_ids, ...) -> pos, yaw    │          │
│  │  - gen_goal(env_ids, ...) -> pos           │          │
│  │  - validate(positions, ...) -> bool[]      │          │
│  └───────────────────────────────────────────┘          │
│           ▲ uses                                        │
│  ┌────────┴──────────────────────────────────┐          │
│  │ Shared building blocks (nepher.utils)     │          │
│  │  - FastSpawnSampler                       │          │
│  │  - PrebakedPairSampler                    │          │
│  └───────────────────────────────────────────┘          │
└──────────────────────┬──────────────────────────────────┘
                       │ provides strategy
                       ▼
┌─────────────────────────────────────────────────────────┐
│  AbstractNavigationEnvCfg                               │
│                                                         │
│  position_strategy: PositionStrategy | None             │
│                                                         │
│  gen_bot_pos(...)   → delegates to strategy             │
│  gen_goal_pos(...)  → delegates to strategy             │
│  validate_positions(...) → delegates to strategy        │
│                                                         │
│  + env_origins offset logic (shared, write-once)        │
│  + goal_z_offset application                            │
│  + min/max start-goal distance enforcement              │
└─────────────────────────────────────────────────────────┘
         ▲                          ▲
         │                          │
  PresetNavigationEnvCfg    UsdNavigationEnvCfg
  (thin: terrain cfg,       (thin: terrain cfg,
   lighting, obstacles)      USD scene, lighting)
```

### 3.1 The `PositionStrategy` Protocol

```python
from typing import Protocol, runtime_checkable
import torch

@runtime_checkable
class PositionStrategy(Protocol):
    """Pluggable position generation strategy.

    Implementations produce LOCAL coordinates (relative to sub-terrain
    or cell origin). The EnvCfg layer adds env_origins, device transfer,
    and z-offset.
    """

    def gen_spawn(
        self,
        n: int,
        *,
        device: str | torch.device = "cpu",
        env_ids: torch.Tensor | None = None,
        **kwargs,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Return (positions (n,3), yaws (n,)) in local coords."""
        ...

    def gen_goal(
        self,
        n: int,
        *,
        device: str | torch.device = "cpu",
        env_ids: torch.Tensor | None = None,
        spawn_positions: torch.Tensor | None = None,
        **kwargs,
    ) -> torch.Tensor:
        """Return goal positions (n,3) in local coords."""
        ...

    def validate(
        self,
        positions: torch.Tensor,
        **kwargs,
    ) -> torch.Tensor:
        """Return boolean mask (n,) — True = valid."""
        ...
```

Key design choices:

- **Local coordinates.** Strategies know nothing about `env_origins` or Isaac
  Lab tiling. This makes them pure numerical objects, testable with plain
  tensors.
- **`env_ids` is optional.** Strategies that need deterministic assignment
  (e.g. pre-baked pairs) use it; strategies that sample randomly ignore it.
- **`spawn_positions` in `gen_goal`.** Enables strategies that enforce
  min-distance between spawn and goal without coupling to the caller's state.

### 3.2 Built-in Strategy Implementations

These live in `nepher/utils/strategies/` and wrap genuinely reusable patterns.
The bar for inclusion is high — a strategy belongs here only if multiple
unrelated environments would use it. Environment-specific algorithms belong
in the environment bundle, not in core.

| Class | Wraps | Use case |
|-------|-------|----------|
| `OccupancySamplerStrategy` | `FastSpawnSampler` | Real-world / USD scenes with occupancy maps or rectangular spawn areas. |
| `PrebakedPairStrategy` | flat pair list (JSON, tensor) | Environments with offline-generated start/end pairs (e.g. procedural terrains). |
| `UniformBoxStrategy` | — | Trivial fallback: uniform random in an axis-aligned bounding box. |
| `CompositeStrategy` | any N strategies | Weighted random delegation (e.g. 70% room A, 30% room B). |

Environments pick or compose these. Custom environments can implement the
protocol directly for bespoke logic — no need to wrap a core utility.

### 3.3 Changes to `AbstractNavigationEnvCfg`

```python
@configclass
class AbstractNavigationEnvCfg(BaseEnvCfg):

    # --- new field ---
    position_strategy: PositionStrategy | None = None

    # --- gen_bot_pos becomes a thin adapter ---
    def gen_bot_pos(self, env_ids, env_origins, device="cpu", **kw):
        strategy = self._resolve_strategy()
        local_pos, yaws = strategy.gen_spawn(
            len(env_ids), device=device, env_ids=env_ids, **kw,
        )
        local_pos[:, :2] += env_origins[env_ids, :2]
        return local_pos, yaws

    # --- gen_goal_pos becomes a thin adapter ---
    def gen_goal_pos(self, env_ids, env_origins, device="cpu", **kw):
        strategy = self._resolve_strategy()
        local_goals = strategy.gen_goal(
            len(env_ids), device=device, env_ids=env_ids, **kw,
        )
        local_goals[:, 2] = self.goal_z_offset
        local_goals[:, :2] += env_origins[env_ids, :2]
        return local_goals

    # --- validate_positions delegates ---
    def validate_positions(self, positions, env_origins, device="cpu", **kw):
        strategy = self._resolve_strategy()
        return strategy.validate(positions, **kw)

    def _resolve_strategy(self) -> PositionStrategy:
        if self.position_strategy is None:
            raise NotImplementedError(
                "No position_strategy set. Either assign one or override "
                "gen_bot_pos / gen_goal_pos in your subclass."
            )
        return self.position_strategy
```

Subclasses can still override `gen_bot_pos` / `gen_goal_pos` directly for
backward compatibility, but the **recommended path** is to set
`position_strategy`.

### 3.4 Min/Max Distance Enforcement (centralized)

Today `min_start_goal_dist` is declared but rarely enforced. The new design
moves enforcement into the abstract base's `gen_goal_pos`:

```python
def gen_goal_pos(self, env_ids, env_origins, device="cpu", **kw):
    spawn_pos = kw.get("robot_positions")  # caller provides if available
    strategy = self._resolve_strategy()

    goals = strategy.gen_goal(
        len(env_ids), device=device, env_ids=env_ids,
        spawn_positions=spawn_pos, **kw,
    )
    goals[:, 2] = self.goal_z_offset
    goals[:, :2] += env_origins[env_ids, :2]

    # Enforce min/max distance (retry loop with fallback)
    if spawn_pos is not None and self.min_start_goal_dist > 0:
        goals = self._enforce_distance_constraints(
            goals, spawn_pos, env_ids, env_origins, device, strategy, **kw,
        )
    return goals
```

This means **every** strategy automatically gets distance enforcement without
duplicating the logic.

---

## 4. What Changes in Each Layer

### 4.1 `nepher/env_cfgs/navigation/abstract_nav_cfg.py`

| Change | Detail |
|--------|--------|
| Add `position_strategy` field | `PositionStrategy \| None = None` |
| Rewrite `gen_bot_pos` | Delegate to strategy + add env_origins. Keep `NotImplementedError` if no strategy and method not overridden. |
| Rewrite `gen_goal_pos` | Delegate to strategy + apply `goal_z_offset` + enforce distance constraints centrally. |
| Rewrite `validate_positions` | Delegate to strategy. |
| Add `_enforce_distance_constraints` | Private helper with configurable retry budget. |
| Keep all existing fields | `success_tolerance`, `goal_z_offset`, `min_start_goal_dist`, etc. remain as task-level knobs. |

### 4.2 `nepher/env_cfgs/navigation/preset_nav_cfg.py`

| Change | Detail |
|--------|--------|
| **Remove** `gen_goal_pos`, `gen_bot_pos`, `validate_positions` implementations | Position generation is no longer a config concern. |
| **Remove** `_get_zone_sampling_data`, `_compute_free_zones`, `clear_zone_cache` | Free-zone computation is removed entirely (see 4.6). |
| **Remove** `_cached_free_zones`, `_cached_zone_bounds`, `_cached_zone_probs` | No more zone caching in configs. |
| **Remove** `_get_obstacle_layout` | Only existed to feed free-zone computation. |
| **Remove** `robot_init_pos_x_range`, `robot_init_pos_y_range` | Fallback ranges were free-zone-specific; strategy defines its own fallback. |
| **Keep** `_get_playground` | Still useful for scene bounds queries. |
| **Keep** `get_terrain_cfg`, `get_obstacle_cfgs`, `get_light_cfgs` | Config's real job: terrain, obstacles, lighting. |
| **No default strategy** | `position_strategy` stays `None`. Environments that subclass this config must provide their own strategy. |

Net effect: `PresetNavigationEnvCfg` shrinks from ~600 lines to ~150 lines
(terrain + obstacles + lighting). It becomes a pure scene-description class.

### 4.3 `nepher/env_cfgs/navigation/usd_nav_cfg.py`

| Change | Detail |
|--------|--------|
| **Remove** `gen_goal_pos`, `gen_bot_pos`, `validate_positions` | Move into `OccupancySamplerStrategy`. |
| **Remove** `_spawn_sampler`, `_get_spawn_sampler` | Strategy owns the sampler lifecycle. |
| **Remove** `_sample_position_from_areas` | Unused helper; strategy handles this. |
| **Add** `__post_init__` wiring | Builds `OccupancySamplerStrategy` from `occupancy_map_yaml`, `spawn_areas`, `exclusion_zones`, etc. |
| **Keep** `SpawnAreaConfig`, `ExclusionZoneConfig` | Still valid config dataclasses, consumed by the strategy constructor. |

### 4.4 `nepher/utils/` — new `strategies/` package

```
nepher/utils/strategies/
├── __init__.py
├── protocol.py           # PositionStrategy protocol
├── occupancy_sampler.py  # OccupancySamplerStrategy (wraps FastSpawnSampler)
├── prebaked_pairs.py     # PrebakedPairStrategy
├── uniform_box.py        # UniformBoxStrategy
└── composite.py          # CompositeStrategy
```

Only genuinely reusable patterns belong here. `fast_spawn_sampler.py` remains
as a lower-level utility consumed by `OccupancySamplerStrategy`.

### 4.5 `environments/obstacle-terrain-v1/`

| File | Change |
|------|--------|
| `obstacle_terrain_preset.py` | **Stop subclassing `PresetNavigationEnvCfg`** entirely. Instead, subclass `AbstractNavigationEnvCfg` directly. In `__post_init__`, build a `PrebakedPairStrategy` from `positions.json` and assign it to `self.position_strategy`. Remove overridden `gen_bot_pos`, `gen_goal_pos`. Keep `get_terrain_cfg`, `get_obstacle_cfgs`, lighting config. |
| `generate_positions.py` | No changes needed. The offline pipeline is already decoupled — it produces `positions.json` which `PrebakedPairStrategy` consumes. |

New `obstacle_terrain_preset.py` structure (conceptual):

```python
@configclass
class ObstacleTerrainPresetCfg(AbstractNavigationEnvCfg):

    terrain_generator: TerrainGeneratorCfg | None = OBSTACLE_TERRAIN_CFG
    # ... terrain, lighting fields ...

    def __post_init__(self):
        pairs = self._load_pairs()
        self.position_strategy = PrebakedPairStrategy(
            starts=pairs["starts"],    # (N, 3) tensor
            ends=pairs["ends"],        # (N, 3) tensor
            yaw_mode="face_goal",      # auto atan2(end - start)
        )

    def get_terrain_cfg(self) -> TerrainImporterCfg:
        # ... same as today ...

    def get_obstacle_cfgs(self) -> dict:
        # ... markers from pairs, same as today ...
```

### 4.6 Deleted files

| Path | Why |
|------|-----|
| `nepher/utils/free_zone_finder.py` | Niche algorithm for computing free rectangles among cuboid obstacles. Only consumed by `PresetNavigationEnvCfg`'s now-removed sampling logic. No other environment uses it. If a future environment needs rectangular free-zone decomposition, it implements that locally — not as a core utility. |

Remove all `FreeZone` and `Rectangle` imports from `preset_nav_cfg.py` and
any re-exports in `nepher/utils/__init__.py`.

---

## 5. `PrebakedPairStrategy` — Detailed Design

This strategy replaces the custom `gen_bot_pos` / `gen_goal_pos` in
`ObstacleTerrainPresetCfg` and can be reused by any environment with
offline-generated position pairs.

```python
class PrebakedPairStrategy:
    """Strategy backed by pre-computed (start, end) position pairs.

    Pair selection: env_ids.long() % num_pairs (deterministic per env).
    Yaw options: 'face_goal' (atan2 toward end), 'random', or fixed float.
    """

    def __init__(
        self,
        starts: torch.Tensor,        # (N, 3)
        ends: torch.Tensor,           # (N, 3)
        yaw_mode: str = "face_goal",  # "face_goal" | "random" | float
        yaw_range: tuple[float, float] = (-math.pi, math.pi),
    ):
        self._starts = starts
        self._ends = ends
        self._yaw_mode = yaw_mode
        self._yaw_range = yaw_range

    @property
    def num_pairs(self) -> int:
        return len(self._starts)

    def gen_spawn(self, n, *, device="cpu", env_ids=None, **kw):
        idx = env_ids.long() % self.num_pairs
        starts = self._starts.to(device)[idx]
        ends = self._ends.to(device)[idx]

        if self._yaw_mode == "face_goal":
            delta = ends - starts
            yaws = torch.atan2(delta[:, 1], delta[:, 0])
        elif self._yaw_mode == "random":
            lo, hi = self._yaw_range
            yaws = torch.rand(n, device=device) * (hi - lo) + lo
        else:
            yaws = torch.full((n,), float(self._yaw_mode), device=device)

        return starts.clone(), yaws

    def gen_goal(self, n, *, device="cpu", env_ids=None, **kw):
        idx = env_ids.long() % self.num_pairs
        return self._ends.to(device)[idx].clone()

    def validate(self, positions, **kw):
        return torch.ones(len(positions), dtype=torch.bool,
                          device=positions.device)
```

### Loading helper (lives alongside or inside the strategy)

```python
@staticmethod
def from_positions_json(path: Path) -> "PrebakedPairStrategy":
    """Load from the obstacle-terrain generate_positions.py output format."""
    with open(path) as f:
        data = json.load(f)
    starts, ends = [], []
    for cell in data["cells"]:
        ox, oy, oz = cell["origin"]
        for pair in cell["pairs"]:
            starts.append([ox + pair["start"][0],
                           oy + pair["start"][1],
                           pair["start"][2]])
            ends.append([ox + pair["end"][0],
                         oy + pair["end"][1],
                         pair["end"][2]])
    return PrebakedPairStrategy(
        starts=torch.tensor(starts, dtype=torch.float32),
        ends=torch.tensor(ends, dtype=torch.float32),
    )
```

---

## 6. Migration Strategy

### Phase 1 — Add protocol + strategies (non-breaking)

1. Create `nepher/utils/strategies/` with the `PositionStrategy` protocol
   and built-in implementations (`PrebakedPairStrategy`,
   `OccupancySamplerStrategy`, `UniformBoxStrategy`, `CompositeStrategy`).
2. Add `position_strategy` field to `AbstractNavigationEnvCfg` (default
   `None`).
3. Wire the abstract base's `gen_bot_pos` / `gen_goal_pos` /
   `validate_positions` to delegate **if** a strategy is set, otherwise
   fall through to `NotImplementedError` (preserves current behavior for
   existing subclasses that override these methods).

**Nothing breaks.** All existing environments continue to work via their
overridden methods.

### Phase 2 — Migrate `obstacle-terrain-v1`

1. Rewrite `ObstacleTerrainPresetCfg` to subclass `AbstractNavigationEnvCfg`
   directly, using `PrebakedPairStrategy`.
2. Remove the override of `gen_bot_pos` / `gen_goal_pos`.
3. Verify parity: same positions for same `env_ids` + same `positions.json`.

### Phase 3 — Strip config classes + delete niche utilities

1. **`PresetNavigationEnvCfg`**: remove all sampling, caching, zone
   computation, and `_get_obstacle_layout`. Keep terrain, obstacle asset
   generation, and lighting. No default strategy.
2. **`UsdNavigationEnvCfg`**: move sampler logic into
   `OccupancySamplerStrategy`, auto-build in `__post_init__`.
3. **Delete `nepher/utils/free_zone_finder.py`**. Remove all imports of
   `FreeZone`, `Rectangle`, `find_free_zones` from config classes.

### Phase 4 — Enforce distance constraints centrally

1. Move min/max distance enforcement into `AbstractNavigationEnvCfg`'s
   `gen_goal_pos` wrapper.
2. Remove per-config distance logic from `UsdNavigationEnvCfg`.
3. Add tests for constraint enforcement.

### Phase 5 — Clean up

1. Remove backward-compat aliases after a deprecation period.
2. Remove unused fields (`robot_init_pos_*` from configs that don't use
   them, unused `allow_robot_spawn` / `allow_goal_spawn` in
   `SpawnAreaConfig`).
3. Audit remaining `nepher/utils/` for any other single-consumer utilities
   that should be moved into the environment that uses them or deleted.

---

## 7. File Change Summary

### New files

| Path | Purpose |
|------|---------|
| `nepher/utils/strategies/__init__.py` | Package exports |
| `nepher/utils/strategies/protocol.py` | `PositionStrategy` protocol definition |
| `nepher/utils/strategies/occupancy_sampler.py` | `OccupancySamplerStrategy` — wraps `FastSpawnSampler` for USD/real-world scenes |
| `nepher/utils/strategies/prebaked_pairs.py` | `PrebakedPairStrategy` — for environments with offline-generated pairs |
| `nepher/utils/strategies/uniform_box.py` | `UniformBoxStrategy` — trivial bounding-box sampler |
| `nepher/utils/strategies/composite.py` | `CompositeStrategy` — weighted multi-strategy delegator |

### Modified files

| Path | Changes |
|------|---------|
| `nepher/env_cfgs/navigation/abstract_nav_cfg.py` | Add `position_strategy` field; rewrite `gen_bot_pos`, `gen_goal_pos`, `validate_positions` to delegate; add `_enforce_distance_constraints`. |
| `nepher/env_cfgs/navigation/preset_nav_cfg.py` | Remove ~400 lines of sampling, caching, zone computation, and obstacle-layout logic. Keep terrain, obstacle asset generation, and lighting. No default strategy — environments must provide one. |
| `nepher/env_cfgs/navigation/usd_nav_cfg.py` | Remove ~150 lines of sampler logic; add `__post_init__` wiring `OccupancySamplerStrategy`; keep USD scene, terrain, lighting config. |
| `nepher/env_cfgs/navigation/__init__.py` | Remove `FreeZone`, `Rectangle` re-exports if present. |
| `environments/obstacle-terrain-v1/obstacle_terrain_preset.py` | Change base class from `PresetNavigationEnvCfg` to `AbstractNavigationEnvCfg`; use `PrebakedPairStrategy`; remove `gen_bot_pos`, `gen_goal_pos` overrides. |

### Deleted files

| Path | Why |
|------|-----|
| `nepher/utils/free_zone_finder.py` | Niche algorithm, only served `PresetNavigationEnvCfg`'s now-removed zone logic. Not reusable. |

### Unchanged files

| Path | Why |
|------|-----|
| `nepher/utils/fast_spawn_sampler.py` | Lower-level utility, consumed by `OccupancySamplerStrategy`. |
| `environments/obstacle-terrain-v1/generate_positions.py` | Offline pipeline, already decoupled. |
| `environments/obstacle-terrain-v1/obstacle_terrains.py` | Terrain definition, unchanged. |
| `environments/obstacle-terrain-v1/positions.json` | Data artifact, unchanged. |
| `nepher/loader/*` | Loaders return config objects; strategy is internal to the config. |

---

## 8. Testing Plan

| Test | What it verifies |
|------|-----------------|
| `test_prebaked_pair_strategy` | Deterministic pair selection by `env_ids`, correct yaw computation, device transfer. |
| `test_occupancy_sampler_strategy` | Samples land on valid cells, exclusion zones respected, min-distance constraint. |
| `test_uniform_box_strategy` | Samples within bounds, correct shape/device. |
| `test_composite_strategy` | Weighted delegation, fallback behavior. |
| `test_abstract_cfg_delegation` | Strategy is called, env_origins applied, goal_z_offset applied, distance enforcement works. |
| `test_backward_compat` | Existing overridden `gen_bot_pos` / `gen_goal_pos` still works when `position_strategy` is `None`. |
| `test_obstacle_terrain_parity` | New `PrebakedPairStrategy` produces identical positions to old `ObstacleTerrainPresetCfg` for same inputs. |

All strategy tests use plain `torch.Tensor` inputs — no Isaac Lab dependency.

---

## 9. Best Practices & Conventions

### For environment authors

1. **Implement `PositionStrategy`**, not `gen_bot_pos` / `gen_goal_pos`
   overrides. Strategies are testable, composable, and reusable.

2. **Use local coordinates.** Your strategy should produce positions relative
   to the sub-terrain or cell origin. The EnvCfg adapter handles
   `env_origins`.

3. **Check built-in strategies first.** Before writing custom logic, check
   if `PrebakedPairStrategy`, `OccupancySamplerStrategy`,
   `UniformBoxStrategy`, or `CompositeStrategy` fits your needs.

4. **Keep environment-specific logic in the environment bundle.** If your
   position generation needs a custom algorithm (e.g. free-zone
   decomposition, graph-based path sampling), implement it as a
   `PositionStrategy` inside your environment folder — not in core.

5. **Offline generation stays in the environment.** Scripts like
   `generate_positions.py` remain in the environment bundle. The strategy
   class simply loads the output.

6. **Keep strategies stateless where possible.** Cached tensors (zone bounds,
   valid cells) are fine, but avoid mutating state across calls. This enables
   safe multi-worker usage.

### For EnvHub core maintainers

1. **Don't add sampling logic to config classes.** If a new sampling pattern
   emerges, create a new strategy implementation.

2. **High bar for core utilities.** A utility belongs in `nepher/utils/`
   only if multiple unrelated environments would use it. Single-consumer
   algorithms belong in the environment that needs them.

3. **Centralize cross-cutting concerns.** Distance constraints, z-offset
   application, and env_origins offsetting belong in
   `AbstractNavigationEnvCfg`, not in individual strategies or configs.

4. **Deprecate, don't delete.** When removing legacy fields or methods, add
   deprecation warnings for one release cycle before removal.

---

## 10. Open Questions

1. **Should `PositionStrategy` be a `@configclass`-compatible dataclass or
   a plain class?** Isaac Lab's `@configclass` has pickling constraints.
   Strategies may need to hold tensors and caches that don't serialize well.
   *Recommendation*: keep strategies as plain classes; configs hold only the
   *parameters* needed to construct them, and `__post_init__` does the wiring.

2. **Should `validate` support batch GPU tensor ops?**
   *Recommendation*: start with CPU vectorized (tensor ops, no Python loops);
   GPU can come later if profiling shows it's needed.

3. **Should strategies support dynamic updates (e.g. obstacle moved)?**
   *Recommendation*: add an optional `reset()` to the protocol with a
   default no-op. Most strategies are immutable after construction.
