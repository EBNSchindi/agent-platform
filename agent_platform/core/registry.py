"""
Agent Registry
Central registry for all agents across modules.
Enables agent discovery, cross-module communication, and module management.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AgentInfo:
    """Information about a registered agent"""
    agent_id: str
    module_name: str
    agent_name: str
    agent_type: str
    description: str
    capabilities: List[str] = field(default_factory=list)
    registered_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModuleInfo:
    """Information about a registered module"""
    name: str
    version: str
    description: str
    active: bool = True
    registered_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentRegistry:
    """
    Central registry for all agents across modules.

    Responsibilities:
    - Module registration and management
    - Agent registration and discovery
    - Cross-module agent communication
    - Shared context store
    """

    def __init__(self):
        self.modules: Dict[str, ModuleInfo] = {}
        self.agents: Dict[str, Any] = {}  # agent_id -> Agent instance
        self.agent_info: Dict[str, AgentInfo] = {}  # agent_id -> AgentInfo
        self.context_store: Dict[str, Any] = {}

    # ========================================================================
    # MODULE MANAGEMENT
    # ========================================================================

    def register_module(
        self,
        name: str,
        version: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ModuleInfo:
        """
        Register a new module with the platform.

        Args:
            name: Module name (e.g., "email")
            version: Module version (e.g., "1.0.0")
            description: Module description
            metadata: Optional metadata

        Returns:
            ModuleInfo instance
        """
        if name in self.modules:
            print(f"⚠️  Module '{name}' already registered, updating...")

        module_info = ModuleInfo(
            name=name,
            version=version,
            description=description,
            metadata=metadata or {}
        )

        self.modules[name] = module_info
        print(f"✅ Module registered: {name} v{version}")

        return module_info

    def get_module(self, name: str) -> Optional[ModuleInfo]:
        """Get module information by name"""
        return self.modules.get(name)

    def list_modules(self, active_only: bool = False) -> List[ModuleInfo]:
        """List all registered modules"""
        modules = list(self.modules.values())
        if active_only:
            modules = [m for m in modules if m.active]
        return modules

    def activate_module(self, name: str):
        """Activate a module"""
        if name in self.modules:
            self.modules[name].active = True
            print(f"✅ Module activated: {name}")
        else:
            raise ValueError(f"Module '{name}' not found")

    def deactivate_module(self, name: str):
        """Deactivate a module"""
        if name in self.modules:
            self.modules[name].active = False
            print(f"⏸️  Module deactivated: {name}")
        else:
            raise ValueError(f"Module '{name}' not found")

    # ========================================================================
    # AGENT MANAGEMENT
    # ========================================================================

    def register_agent(
        self,
        module_name: str,
        agent_name: str,
        agent_instance: Any,
        agent_type: str,
        description: str = "",
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Register an agent with the registry.

        Args:
            module_name: Name of the module this agent belongs to
            agent_name: Name of the agent
            agent_instance: The actual Agent instance
            agent_type: Type of agent (e.g., "classifier", "responder")
            description: Agent description
            capabilities: List of capabilities (e.g., ["email_classification", "spam_detection"])
            metadata: Optional metadata

        Returns:
            agent_id: Unique identifier for the agent (module_name.agent_name)
        """
        # Generate unique agent ID
        agent_id = f"{module_name}.{agent_name}"

        if agent_id in self.agents:
            print(f"⚠️  Agent '{agent_id}' already registered, updating...")

        # Store agent instance
        self.agents[agent_id] = agent_instance

        # Store agent info
        agent_info = AgentInfo(
            agent_id=agent_id,
            module_name=module_name,
            agent_name=agent_name,
            agent_type=agent_type,
            description=description,
            capabilities=capabilities or [],
            metadata=metadata or {}
        )
        self.agent_info[agent_id] = agent_info

        print(f"✅ Agent registered: {agent_id}")

        return agent_id

    def get_agent(self, agent_id: str) -> Optional[Any]:
        """
        Get agent instance by ID.

        Args:
            agent_id: Full agent ID (module_name.agent_name)

        Returns:
            Agent instance or None
        """
        return self.agents.get(agent_id)

    def get_agent_info(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent information by ID"""
        return self.agent_info.get(agent_id)

    def list_agents(
        self,
        module_name: Optional[str] = None,
        agent_type: Optional[str] = None,
        capability: Optional[str] = None
    ) -> List[AgentInfo]:
        """
        List agents with optional filtering.

        Args:
            module_name: Filter by module
            agent_type: Filter by agent type
            capability: Filter by capability

        Returns:
            List of AgentInfo instances
        """
        agents = list(self.agent_info.values())

        if module_name:
            agents = [a for a in agents if a.module_name == module_name]

        if agent_type:
            agents = [a for a in agents if a.agent_type == agent_type]

        if capability:
            agents = [a for a in agents if capability in a.capabilities]

        return agents

    def discover_agents(self, capability: str) -> List[str]:
        """
        Discover agents by capability.

        Args:
            capability: Capability to search for (e.g., "email_classification")

        Returns:
            List of agent IDs with the specified capability
        """
        return [
            agent_id
            for agent_id, info in self.agent_info.items()
            if capability in info.capabilities
        ]

    # ========================================================================
    # CONTEXT STORE (Shared Memory)
    # ========================================================================

    def set_context(self, key: str, value: Any):
        """Store value in shared context"""
        self.context_store[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Retrieve value from shared context"""
        return self.context_store.get(key, default)

    def delete_context(self, key: str):
        """Delete value from shared context"""
        if key in self.context_store:
            del self.context_store[key]

    def clear_context(self):
        """Clear all shared context"""
        self.context_store.clear()

    # ========================================================================
    # UTILITY
    # ========================================================================

    def get_stats(self) -> Dict[str, int]:
        """Get registry statistics"""
        return {
            "total_modules": len(self.modules),
            "active_modules": len([m for m in self.modules.values() if m.active]),
            "total_agents": len(self.agents),
            "context_keys": len(self.context_store),
        }

    def print_summary(self):
        """Print a summary of the registry"""
        print("\n" + "="*60)
        print("AGENT PLATFORM REGISTRY")
        print("="*60)

        stats = self.get_stats()
        print(f"📦 Modules: {stats['active_modules']}/{stats['total_modules']} active")
        print(f"🤖 Agents: {stats['total_agents']} registered")
        print(f"💾 Context Store: {stats['context_keys']} keys")

        print("\n📦 MODULES:")
        for module in self.list_modules():
            status = "✅" if module.active else "⏸️ "
            print(f"  {status} {module.name} v{module.version} - {module.description}")

        print("\n🤖 AGENTS:")
        for agent_info in self.list_agents():
            print(f"  • {agent_info.agent_id}")
            print(f"    Type: {agent_info.agent_type}")
            if agent_info.capabilities:
                print(f"    Capabilities: {', '.join(agent_info.capabilities)}")

        print("="*60 + "\n")


# Global registry instance
_registry = None


def get_registry() -> AgentRegistry:
    """Get the global agent registry instance"""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry
