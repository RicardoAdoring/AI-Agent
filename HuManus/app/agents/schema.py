from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    ERROR = "ERROR"


@dataclass
class AgentStep:
    index: int
    thought: str = ""
    action: str = ""
    action_input: dict[str, Any] = field(default_factory=dict)
    observation: str = ""
    status: str = "pending"
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "thought": self.thought,
            "action": self.action,
            "action_input": self.action_input,
            "observation": self.observation,
            "status": self.status,
            "error": self.error,
        }


@dataclass
class AgentRunResult:
    answer: str
    steps: list[AgentStep]
    log_path: str
    finished_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "steps": [step.to_dict() for step in self.steps],
            "log_path": self.log_path,
            "finished_reason": self.finished_reason,
        }
