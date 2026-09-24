"""
Project Extra — Task Blueprint & Directed Acyclic Graph (DAG) Subsystem
Provides hierarchical planning, milestone dependency tracking, and state persistence
for long-horizon desktop automation tasks.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("Extra-Composer-Blueprint")

_EXTRA_HOME = Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or ".") / ".extra"
_BLUEPRINTS_DIR = _EXTRA_HOME / "blueprints"


class MilestoneStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


@dataclass
class Milestone:
    """
    An atomic, verifiable milestone within a long-horizon task graph.
    """
    id: str
    name: str
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    runtime: Optional[str] = None  # e.g., 'python', 'blender_bpy', 'powershell', 'gui'
    payload: Optional[Dict[str, Any]] = None  # script, actions, or arguments
    expected_artifacts: List[str] = field(default_factory=list)
    acceptance_criteria: Dict[str, Any] = field(default_factory=dict)
    timeout_sec: float = 120.0
    status: MilestoneStatus = MilestoneStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Milestone:
        d = dict(data)
        # Resilient mapping: if 'name' is missing or empty, fall back to 'title'
        if not d.get("name") and d.get("title"):
            d["name"] = d.get("title")
        if "status" in d and isinstance(d["status"], str):
            try:
                d["status"] = MilestoneStatus(d["status"])
            except ValueError:
                d["status"] = MilestoneStatus.PENDING
        # Filter to only valid dataclass field names to prevent unexpected keyword argument errors
        known_fields = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in d.items() if k in known_fields}
        if "id" not in filtered or not filtered["id"]:
            import uuid
            filtered["id"] = f"m_{uuid.uuid4().hex[:8]}"
        if "name" not in filtered or not filtered["name"]:
            filtered["name"] = filtered.get("id", "milestone")
        return cls(**filtered)


class TaskDAG:
    """
    Manages dependency resolution and validation for milestones.
    Prevents circular dependencies and determines runnable sub-tasks.
    """

    def __init__(self, milestones: Dict[str, Milestone]) -> None:
        self.milestones = milestones
        self.validate()

    def validate(self) -> None:
        """Validates that all dependencies exist and graph has no cycles."""
        for m_id, m in self.milestones.items():
            for dep in m.dependencies:
                if dep not in self.milestones:
                    raise ValueError(f"Milestone '{m_id}' depends on non-existent milestone '{dep}'")

        # Cycle detection via DFS
        visited: Dict[str, int] = {}  # 0 = visiting, 1 = visited

        def visit(node: str) -> None:
            if visited.get(node) == 0:
                raise ValueError(f"Circular dependency detected involving milestone '{node}'")
            if visited.get(node) == 1:
                return
            visited[node] = 0
            for dep in self.milestones[node].dependencies:
                visit(dep)
            visited[node] = 1

        for m_id in self.milestones:
            if m_id not in visited:
                visit(m_id)

    def get_runnable_milestones(self) -> List[Milestone]:
        """Returns all PENDING milestones whose dependencies are COMPLETED."""
        completed_ids = {
            m.id for m in self.milestones.values()
            if m.status in (MilestoneStatus.COMPLETED, MilestoneStatus.SKIPPED)
        }
        runnable = []
        for m in self.milestones.values():
            if m.status == MilestoneStatus.PENDING:
                if all(dep in completed_ids for dep in m.dependencies):
                    runnable.append(m)
        return runnable

    def get_descendants(self, milestone_id: str) -> Set[str]:
        """Finds all milestones that directly or transitively depend on milestone_id."""
        descendants: Set[str] = set()
        queue = [milestone_id]
        while queue:
            curr = queue.pop(0)
            for m in self.milestones.values():
                if curr in m.dependencies and m.id not in descendants:
                    descendants.add(m.id)
                    queue.append(m.id)
        return descendants


class TaskBlueprint:
    """
    The master declarative specification for a long-horizon desktop task.
    Maintains the TaskDAG, active execution state, checkpoints, and history.
    """

    def __init__(
        self,
        title: str,
        task_id: Optional[str] = None,
        task_type: str = "general",
        milestones: Optional[List[Milestone]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        raw_id = task_id or f"bp_{uuid.uuid4().hex[:10]}"
        self.task_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", raw_id)
        self.title = title
        self.task_type = task_type
        self.milestones: Dict[str, Milestone] = {}
        if milestones:
            for m in milestones:
                self.milestones[m.id] = m
        self.dag = TaskDAG(self.milestones)
        self.active_milestone_id: Optional[str] = None
        self.history: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = metadata or {}
        self.created_at: float = time.time()
        self.updated_at: float = self.created_at

    def add_milestone(self, milestone: Milestone) -> None:
        self.milestones[milestone.id] = milestone
        self.dag = TaskDAG(self.milestones)
        self.updated_at = time.time()

    def get_next_runnable(self) -> List[Milestone]:
        return self.dag.get_runnable_milestones()

    def start_milestone(self, milestone_id: str) -> Milestone:
        if milestone_id not in self.milestones:
            raise KeyError(f"Milestone '{milestone_id}' not found in blueprint")
        m = self.milestones[milestone_id]
        m.status = MilestoneStatus.RUNNING
        m.started_at = time.time()
        self.active_milestone_id = milestone_id
        self.updated_at = time.time()
        self.history.append({
            "event": "milestone_started",
            "milestone_id": milestone_id,
            "timestamp": m.started_at,
        })
        logger.info("[Blueprint:%s] Milestone '%s' started", self.task_id, milestone_id)
        return m

    def complete_milestone(
        self,
        milestone_id: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> Milestone:
        if milestone_id not in self.milestones:
            raise KeyError(f"Milestone '{milestone_id}' not found in blueprint")
        m = self.milestones[milestone_id]
        m.status = MilestoneStatus.COMPLETED
        m.completed_at = time.time()
        m.result = result or {}
        if self.active_milestone_id == milestone_id:
            self.active_milestone_id = None
        self.updated_at = time.time()
        self.history.append({
            "event": "milestone_completed",
            "milestone_id": milestone_id,
            "result": m.result,
            "timestamp": m.completed_at,
        })
        logger.info("[Blueprint:%s] Milestone '%s' completed successfully", self.task_id, milestone_id)
        return m

    def fail_milestone(self, milestone_id: str, error: str) -> Milestone:
        if milestone_id not in self.milestones:
            raise KeyError(f"Milestone '{milestone_id}' not found in blueprint")
        m = self.milestones[milestone_id]
        m.status = MilestoneStatus.FAILED
        m.error = error
        m.completed_at = time.time()
        if self.active_milestone_id == milestone_id:
            self.active_milestone_id = None
        self.updated_at = time.time()
        self.history.append({
            "event": "milestone_failed",
            "milestone_id": milestone_id,
            "error": error,
            "timestamp": m.completed_at,
        })
        logger.warning("[Blueprint:%s] Milestone '%s' failed: %s", self.task_id, milestone_id, error)
        return m

    def rollback_to(self, milestone_id: str) -> List[str]:
        """
        Rolls back the target milestone and all its downstream dependents to PENDING.
        Enables non-destructive recovery from mid-pipeline errors.
        """
        if milestone_id not in self.milestones:
            raise KeyError(f"Milestone '{milestone_id}' not found in blueprint")

        to_reset = {milestone_id} | self.dag.get_descendants(milestone_id)
        for m_id in to_reset:
            m = self.milestones[m_id]
            m.status = MilestoneStatus.PENDING
            m.result = None
            m.error = None
            m.started_at = None
            m.completed_at = None

        if self.active_milestone_id in to_reset:
            self.active_milestone_id = None

        self.updated_at = time.time()
        self.history.append({
            "event": "rollback",
            "target_milestone_id": milestone_id,
            "reset_milestones": list(to_reset),
            "timestamp": self.updated_at,
        })
        logger.info("[Blueprint:%s] Rolled back %d milestones starting from '%s'", self.task_id, len(to_reset), milestone_id)
        return list(to_reset)

    @property
    def is_complete(self) -> bool:
        """Returns True if every milestone is COMPLETED or SKIPPED."""
        return all(m.status in (MilestoneStatus.COMPLETED, MilestoneStatus.SKIPPED) for m in self.milestones.values())

    @property
    def has_failed(self) -> bool:
        """Returns True if any milestone has failed and cannot proceed."""
        return any(m.status == MilestoneStatus.FAILED for m in self.milestones.values())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "task_type": self.task_type,
            "milestones": {m_id: m.to_dict() for m_id, m in self.milestones.items()},
            "active_milestone_id": self.active_milestone_id,
            "is_complete": self.is_complete,
            "has_failed": self.has_failed,
            "history": self.history,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TaskBlueprint:
        milestones = [Milestone.from_dict(m_data) for m_data in data.get("milestones", {}).values()]
        bp = cls(
            title=data.get("title", "Untitled Task"),
            task_id=data.get("task_id"),
            task_type=data.get("task_type", "general"),
            milestones=milestones,
            metadata=data.get("metadata", {}),
        )
        bp.active_milestone_id = data.get("active_milestone_id")
        bp.history = data.get("history", [])
        bp.created_at = data.get("created_at", time.time())
        bp.updated_at = data.get("updated_at", time.time())
        return bp

    def save(self, file_path: Optional[Path] = None) -> Path:
        target = file_path or (_BLUEPRINTS_DIR / f"{self.task_id}.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return target

    @classmethod
    def load(cls, file_path: Path) -> TaskBlueprint:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return cls.from_dict(data)
