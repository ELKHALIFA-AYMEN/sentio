"""Synthetic support conversations for a fictional telecom operator."""

from sentio_simulator.catalog import OPERATOR_NAME
from sentio_simulator.generator import Conversation, GeneratorConfig, generate_conversation
from sentio_simulator.scenarios import SCENARIOS, Incident, Scenario, ScenarioName

__all__ = [
    "OPERATOR_NAME",
    "SCENARIOS",
    "Conversation",
    "GeneratorConfig",
    "Incident",
    "Scenario",
    "ScenarioName",
    "generate_conversation",
]
