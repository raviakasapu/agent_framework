"""
Context Configuration Service

Loads and manages context configuration from YAML with ENV variable overrides.
Provides a centralized way to control what context is included in prompts
and how it's truncated.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import yaml

from ..logging import get_logger

logger = get_logger()


@dataclass
class TruncationConfig:
    """Truncation limits for various context types."""
    strategic_plan: int = 2000
    director_context: int = 4000
    data_model_context: int = 6000
    observation: int = 1500
    tool_args: int = 500
    previous_output: int = 5000
    manifest: int = 6000

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TruncationConfig":
        return cls(
            strategic_plan=data.get("strategic_plan", 2000),
            director_context=data.get("director_context", 4000),
            data_model_context=data.get("data_model_context", 6000),
            observation=data.get("observation", 1500),
            tool_args=data.get("tool_args", 500),
            previous_output=data.get("previous_output", 5000),
            manifest=data.get("manifest", 6000),
        )


@dataclass
class HistoryConfig:
    """History inclusion settings."""
    max_conversation_turns: int = 10
    max_execution_traces: int = 20
    include_conversation: bool = True
    include_traces: bool = True
    include_global_updates: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HistoryConfig":
        return cls(
            max_conversation_turns=data.get("max_conversation_turns", 10),
            max_execution_traces=data.get("max_execution_traces", 20),
            include_conversation=data.get("include_conversation", True),
            include_traces=data.get("include_traces", True),
            include_global_updates=data.get("include_global_updates", True),
        )


@dataclass
class ContextSection:
    """Configuration for a context section."""
    name: str
    enabled: bool = True
    position: int = 0
    include: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)
    max_outputs: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextSection":
        return cls(
            name=data.get("name", ""),
            enabled=data.get("enabled", True),
            position=data.get("position", 0),
            include=data.get("include", []),
            exclude=data.get("exclude", []),
            max_outputs=data.get("max_outputs"),
        )


@dataclass
class PlannerConfig:
    """Configuration for a specific planner."""
    name: str
    truncation: TruncationConfig
    history: HistoryConfig
    context_sections: List[ContextSection] = field(default_factory=list)

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any], defaults: "PlannerConfig") -> "PlannerConfig":
        # Merge truncation with defaults
        trunc_data = {**defaults.truncation.__dict__}
        trunc_data.update(data.get("truncation", {}))

        # Merge history with defaults
        hist_data = {**defaults.history.__dict__}
        hist_data.update(data.get("history", {}))

        # Parse context sections
        sections = [
            ContextSection.from_dict(s)
            for s in data.get("context_sections", [])
        ]

        return cls(
            name=name,
            truncation=TruncationConfig.from_dict(trunc_data),
            history=HistoryConfig.from_dict(hist_data),
            context_sections=sorted(sections, key=lambda s: s.position),
        )


class ContextConfig:
    """
    Central configuration manager for context building.

    Loads configuration from YAML with ENV variable overrides.
    Provides per-planner settings for truncation, history, and context sections.
    """

    _instance: Optional["ContextConfig"] = None
    _config_path: Optional[str] = None

    def __init__(self, config_path: Optional[str] = None) -> None:
        self._defaults = PlannerConfig(
            name="defaults",
            truncation=TruncationConfig(),
            history=HistoryConfig(),
            context_sections=[],
        )
        self._planners: Dict[str, PlannerConfig] = {}
        self._log_truncation: bool = True
        self._log_truncation_level: str = "INFO"
        self._env_overrides: Dict[str, str] = {}

        if config_path:
            self._load_from_yaml(config_path)

        # Apply ENV overrides last (highest priority)
        self._apply_env_overrides()

    @classmethod
    def get_instance(cls, config_path: Optional[str] = None) -> "ContextConfig":
        """Get singleton instance, optionally loading from a config file."""
        if cls._instance is None or (config_path and config_path != cls._config_path):
            cls._instance = cls(config_path)
            cls._config_path = config_path
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance (for testing)."""
        cls._instance = None
        cls._config_path = None

    def _load_from_yaml(self, config_path: str) -> None:
        """Load configuration from YAML file."""
        path = Path(config_path)
        if not path.exists():
            # Try relative to package
            package_dir = Path(__file__).parent.parent
            path = package_dir / "configs" / "context_config.yaml"

        if not path.exists():
            logger.warning(f"Context config not found at {config_path}, using defaults")
            return

        try:
            text = path.read_text(encoding="utf-8")
            text = os.path.expandvars(text)
            raw = yaml.safe_load(text) or {}

            if raw.get("kind") != "ContextConfig":
                logger.warning(f"Invalid context config kind: {raw.get('kind')}, expected ContextConfig")
                return

            spec = raw.get("spec", {})
            self._parse_spec(spec)
            self._env_overrides = raw.get("env_overrides", {})

            logger.info(f"Loaded context config from {path}")

        except Exception as e:
            logger.error(f"Failed to load context config from {config_path}: {e}")

    def _parse_spec(self, spec: Dict[str, Any]) -> None:
        """Parse the spec section of the config."""
        # Parse defaults
        defaults_data = spec.get("defaults", {})
        self._defaults = PlannerConfig(
            name="defaults",
            truncation=TruncationConfig.from_dict(defaults_data.get("truncation", {})),
            history=HistoryConfig.from_dict(defaults_data.get("history", {})),
            context_sections=[],
        )
        self._log_truncation = defaults_data.get("log_truncation", True)
        self._log_truncation_level = defaults_data.get("log_truncation_level", "INFO")

        # Parse per-planner configs
        planners_data = spec.get("planners", {})
        for planner_name, planner_data in planners_data.items():
            self._planners[planner_name] = PlannerConfig.from_dict(
                planner_name, planner_data, self._defaults
            )

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides."""
        # Global truncation overrides
        env_mappings = {
            "AGENT_STRATEGIC_PLAN_TRUNCATE_LEN": ("truncation", "strategic_plan"),
            "AGENT_DIRECTOR_CONTEXT_TRUNCATE_LEN": ("truncation", "director_context"),
            "AGENT_DATA_MODEL_CONTEXT_TRUNCATE_LEN": ("truncation", "data_model_context"),
            "AGENT_OBSERVATION_TRUNCATE_LEN": ("truncation", "observation"),
            "AGENT_TOOL_ARGS_TRUNCATE_LEN": ("truncation", "tool_args"),
            "AGENT_PREVIOUS_OUTPUT_TRUNCATE_LEN": ("truncation", "previous_output"),
            "AGENT_MANIFEST_TRUNCATE_LEN": ("truncation", "manifest"),
            # Global history overrides
            "AGENT_MAX_CONVERSATION_TURNS": ("history", "max_conversation_turns"),
            "AGENT_MAX_EXECUTION_TRACES": ("history", "max_execution_traces"),
            "AGENT_INCLUDE_CONVERSATION": ("history", "include_conversation"),
            "AGENT_INCLUDE_TRACES": ("history", "include_traces"),
            "AGENT_INCLUDE_GLOBAL_UPDATES": ("history", "include_global_updates"),
            # Logging
            "AGENT_LOG_TRUNCATION": ("log", "truncation"),
        }

        for env_var, (category, field) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                self._apply_env_value(category, field, value)

        # Per-planner overrides
        self._apply_planner_env_overrides()

    def _apply_env_value(self, category: str, field: str, value: str) -> None:
        """Apply a single ENV value to config."""
        if category == "truncation":
            try:
                int_value = int(value)
                setattr(self._defaults.truncation, field, int_value)
                # Also apply to all planners
                for planner in self._planners.values():
                    setattr(planner.truncation, field, int_value)
            except ValueError:
                logger.warning(f"Invalid integer value for {field}: {value}")

        elif category == "history":
            if field in ("include_conversation", "include_traces", "include_global_updates"):
                bool_value = value.lower() in ("1", "true", "yes")
                setattr(self._defaults.history, field, bool_value)
                for planner in self._planners.values():
                    setattr(planner.history, field, bool_value)
            else:
                try:
                    int_value = int(value)
                    setattr(self._defaults.history, field, int_value)
                    for planner in self._planners.values():
                        setattr(planner.history, field, int_value)
                except ValueError:
                    logger.warning(f"Invalid integer value for {field}: {value}")

        elif category == "log" and field == "truncation":
            self._log_truncation = value.lower() in ("1", "true", "yes")

    def _apply_planner_env_overrides(self) -> None:
        """Apply per-planner ENV overrides."""
        # ReAct planner overrides
        react_config = self.get_planner_config("react")

        obs_len = os.getenv("AGENT_REACT_OBS_TRUNCATE_LEN")
        if obs_len:
            try:
                react_config.truncation.observation = int(obs_len)
            except ValueError:
                pass

        include_hist = os.getenv("AGENT_REACT_INCLUDE_HISTORY")
        if include_hist:
            react_config.history.include_conversation = include_hist.lower() in ("1", "true", "yes")

        include_traces = os.getenv("AGENT_REACT_INCLUDE_TRACES")
        if include_traces:
            react_config.history.include_traces = include_traces.lower() in ("1", "true", "yes")

        include_global = os.getenv("AGENT_REACT_INCLUDE_GLOBAL_UPDATES")
        if include_global:
            react_config.history.include_global_updates = include_global.lower() in ("1", "true", "yes")

        max_hist = os.getenv("AGENT_REACT_MAX_HISTORY_MESSAGES")
        if max_hist:
            try:
                react_config.history.max_execution_traces = int(max_hist)
            except ValueError:
                pass

        # Router planner overrides
        router_config = self.get_planner_config("router")

        router_max = os.getenv("AGENT_ROUTER_MAX_HISTORY_MESSAGES")
        if router_max:
            try:
                router_config.history.max_conversation_turns = int(router_max)
            except ValueError:
                pass

        router_include = os.getenv("AGENT_ROUTER_INCLUDE_HISTORY")
        if router_include:
            router_config.history.include_conversation = router_include.lower() in ("1", "true", "yes")

        router_plan_len = os.getenv("AGENT_ROUTER_STRATEGIC_PLAN_TRUNCATE_LEN")
        if router_plan_len:
            try:
                router_config.truncation.strategic_plan = int(router_plan_len)
            except ValueError:
                pass

        # Strategic planner overrides
        strategic_config = self.get_planner_config("strategic")

        orch_turns = os.getenv("AGENT_ORCHESTRATOR_MAX_HISTORY_TURNS")
        if orch_turns:
            try:
                strategic_config.history.max_conversation_turns = int(orch_turns)
            except ValueError:
                pass

        include_with_director = os.getenv("STRATEGIC_INCLUDE_HISTORY_WITH_DIRECTOR")
        if include_with_director:
            strategic_config.history.include_conversation = include_with_director.lower() in ("1", "true", "yes")

    def get_planner_config(self, planner_name: str) -> PlannerConfig:
        """Get configuration for a specific planner."""
        if planner_name not in self._planners:
            # Create a new config inheriting from defaults
            self._planners[planner_name] = PlannerConfig(
                name=planner_name,
                truncation=TruncationConfig(**self._defaults.truncation.__dict__),
                history=HistoryConfig(**self._defaults.history.__dict__),
                context_sections=[],
            )
        return self._planners[planner_name]

    def get_truncation_limit(self, planner_name: str, field: str) -> int:
        """Get truncation limit for a field in a specific planner."""
        config = self.get_planner_config(planner_name)
        return getattr(config.truncation, field, getattr(self._defaults.truncation, field, 1000))

    def should_include_conversation(self, planner_name: str) -> bool:
        """Check if conversation history should be included."""
        config = self.get_planner_config(planner_name)
        return config.history.include_conversation

    def should_include_traces(self, planner_name: str) -> bool:
        """Check if execution traces should be included."""
        config = self.get_planner_config(planner_name)
        return config.history.include_traces

    def should_include_global_updates(self, planner_name: str) -> bool:
        """Check if global updates should be included."""
        config = self.get_planner_config(planner_name)
        return config.history.include_global_updates

    def get_max_conversation_turns(self, planner_name: str) -> int:
        """Get maximum conversation turns for a planner."""
        config = self.get_planner_config(planner_name)
        return config.history.max_conversation_turns

    def get_max_execution_traces(self, planner_name: str) -> int:
        """Get maximum execution traces for a planner."""
        config = self.get_planner_config(planner_name)
        return config.history.max_execution_traces

    def get_context_sections(self, planner_name: str) -> List[ContextSection]:
        """Get ordered context sections for a planner."""
        config = self.get_planner_config(planner_name)
        return [s for s in config.context_sections if s.enabled]

    def should_log_truncation(self) -> bool:
        """Check if truncation should be logged."""
        return self._log_truncation

    def truncate_with_logging(
        self,
        content: str,
        limit: int,
        field_name: str,
        planner_name: str = "unknown",
    ) -> str:
        """
        Truncate content and optionally log the truncation.

        Args:
            content: The content to truncate
            limit: Maximum character limit
            field_name: Name of the field being truncated (for logging)
            planner_name: Name of the planner (for logging)

        Returns:
            Truncated content with marker if truncated
        """
        if len(content) <= limit:
            return content

        truncated = content[:limit]
        truncated_chars = len(content) - limit

        if self._log_truncation:
            log_method = getattr(logger, self._log_truncation_level.lower(), logger.info)
            log_method(
                f"[ContextConfig] Truncated {field_name} for {planner_name}: "
                f"{len(content)} -> {limit} chars (removed {truncated_chars} chars)"
            )

        return truncated + f"\n... [TRUNCATED: {truncated_chars} chars removed]"

    def truncate_json_with_logging(
        self,
        data: Any,
        limit: int,
        field_name: str,
        planner_name: str = "unknown",
        indent: int = 2,
    ) -> str:
        """
        Convert to JSON and truncate with logging.

        Args:
            data: Data to serialize and truncate
            limit: Maximum character limit
            field_name: Name of the field being truncated (for logging)
            planner_name: Name of the planner (for logging)
            indent: JSON indentation

        Returns:
            Truncated JSON string with marker if truncated
        """
        import json

        try:
            content = json.dumps(data, indent=indent)
        except (TypeError, ValueError):
            content = str(data)

        return self.truncate_with_logging(content, limit, field_name, planner_name)


# Global accessor function
def get_context_config(config_path: Optional[str] = None) -> ContextConfig:
    """Get the global context configuration instance."""
    return ContextConfig.get_instance(config_path)
