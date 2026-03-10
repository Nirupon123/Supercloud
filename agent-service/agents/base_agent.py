
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseAgent(ABC):
    def __init__(self, agent_id: str, agent_type: str):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.context = {}
        self.memory = []
    
    @abstractmethod
    async def get_action(self, telemetry_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process telemetry payload and return next action
        Returns: {
            "action":"get_logs|get_metrics|exec_shell|...",
            "parameters":{...}
        }
        """
        pass
    
    def update_context(self, new_context: Dict):
        self.context.update(new_context)
    
    def store_memory(self, interaction: Dict):
        self.memory.append(interaction)
