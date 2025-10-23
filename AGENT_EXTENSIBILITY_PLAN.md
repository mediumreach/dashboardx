# 🔌 Agent Extensibility Architecture Plan

## 📋 Overview

Transform the Agentic RAG Platform into a **plugin-based, framework-agnostic agent system** that allows seamless integration of multiple AI agent frameworks (LangChain, LangGraph, n8n, CrewAI, AutoGen, etc.) without code changes.

---

## 🎯 Goals

1. **Framework Agnostic** - Support any agent framework through adapters
2. **Hot-Swappable** - Switch agents via configuration without redeployment
3. **Multi-Agent Support** - Run multiple agents simultaneously
4. **Easy Integration** - Add new frameworks with minimal code
5. **Unified Interface** - Consistent API regardless of underlying framework
6. **Performance Monitoring** - Compare agent performance across frameworks

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Unified Agent Interface Component             │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   API Layer (FastAPI)                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            Agent Router (Unified API)                 │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Agent Orchestrator                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Agent Registry & Factory                 │  │
│  │  • Discovers available agents                         │  │
│  │  • Routes requests to appropriate adapter             │  │
│  │  • Manages agent lifecycle                            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  LangGraph   │    │  LangChain   │    │     n8n      │
│   Adapter    │    │   Adapter    │    │   Adapter    │
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  LangGraph   │    │  LangChain   │    │ n8n Webhook  │
│   Engine     │    │   Engine     │    │   Executor   │
└──────────────┘    └──────────────┘    └──────────────┘
```

---

## 📦 Component Breakdown

### 1. Base Agent Interface (`backend/app/agents/base.py`)

**Purpose:** Abstract base class defining the contract all agents must implement

**Key Methods:**
- `execute(query, context) -> AgentResponse`
- `execute_streaming(query, context) -> AsyncIterator[AgentResponse]`
- `get_capabilities() -> AgentCapabilities`
- `validate_config() -> bool`
- `health_check() -> HealthStatus`

### 2. Agent Registry (`backend/app/agents/registry.py`)

**Purpose:** Central registry for discovering and managing agent providers

**Features:**
- Auto-discovery of agent adapters
- Dynamic registration/unregistration
- Agent metadata storage
- Version management
- Dependency checking

### 3. Agent Factory (`backend/app/agents/factory.py`)

**Purpose:** Creates agent instances based on configuration

**Features:**
- Configuration-driven instantiation
- Dependency injection
- Connection pooling
- Error handling
- Fallback mechanisms

### 4. Agent Adapters (`backend/app/agents/adapters/`)

**Purpose:** Framework-specific implementations

**Adapters to Create:**
- `langgraph_adapter.py` - Wraps existing LangGraph implementation
- `langchain_adapter.py` - Pure LangChain agents
- `n8n_adapter.py` - n8n workflow integration
- `crewai_adapter.py` - CrewAI multi-agent systems
- `autogen_adapter.py` - Microsoft AutoGen
- `llamaindex_adapter.py` - LlamaIndex agents
- `custom_adapter.py` - Template for custom agents

### 5. Agent Orchestrator (`backend/app/agents/orchestrator.py`)

**Purpose:** Coordinates agent execution and routing

**Features:**
- Request routing
- Load balancing
- Parallel execution
- Result aggregation
- Error recovery

### 6. Configuration System (`backend/app/agents/config.py`)

**Purpose:** Manage agent configurations

**Features:**
- YAML/JSON configuration files
- Environment variable overrides
- Hot-reload support
- Validation schemas
- Default configurations

### 7. Unified API (`backend/app/api/agents_v2.py`)

**Purpose:** Framework-agnostic REST API

**Endpoints:**
- `POST /api/v2/agents/execute` - Execute any agent
- `POST /api/v2/agents/stream` - Stream from any agent
- `GET /api/v2/agents/list` - List available agents
- `GET /api/v2/agents/{agent_id}/info` - Get agent details
- `POST /api/v2/agents/{agent_id}/configure` - Update agent config
- `GET /api/v2/agents/compare` - Compare agent performance

---

## 🔧 Implementation Details

### Phase 1: Core Infrastructure (Week 1)

#### 1.1 Base Agent Interface
```python
# backend/app/agents/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncIterator, Optional
from pydantic import BaseModel

class AgentCapabilities(BaseModel):
    supports_streaming: bool
    supports_tools: bool
    supports_memory: bool
    supports_multimodal: bool
    max_context_length: int
    supported_languages: list[str]

class AgentResponse(BaseModel):
    answer: str
    citations: list[Dict[str, Any]]
    metadata: Dict[str, Any]
    agent_id: str
    execution_time: float

class BaseAgent(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.agent_id = config.get("agent_id")
        self.name = config.get("name")
    
    @abstractmethod
    async def execute(self, query: str, context: Dict[str, Any]) -> AgentResponse:
        """Execute agent with query"""
        pass
    
    @abstractmethod
    async def execute_streaming(self, query: str, context: Dict[str, Any]) -> AsyncIterator[AgentResponse]:
        """Execute agent with streaming"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> AgentCapabilities:
        """Return agent capabilities"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if agent is healthy"""
        pass
```

#### 1.2 Agent Registry
```python
# backend/app/agents/registry.py
from typing import Dict, Type, List
from app.agents.base import BaseAgent

class AgentRegistry:
    _agents: Dict[str, Type[BaseAgent]] = {}
    
    @classmethod
    def register(cls, agent_id: str, agent_class: Type[BaseAgent]):
        """Register an agent adapter"""
        cls._agents[agent_id] = agent_class
    
    @classmethod
    def get(cls, agent_id: str) -> Type[BaseAgent]:
        """Get agent class by ID"""
        return cls._agents.get(agent_id)
    
    @classmethod
    def list_agents(cls) -> List[str]:
        """List all registered agents"""
        return list(cls._agents.keys())
```

#### 1.3 Agent Factory
```python
# backend/app/agents/factory.py
from app.agents.registry import AgentRegistry
from app.agents.base import BaseAgent

class AgentFactory:
    @staticmethod
    async def create_agent(agent_id: str, config: Dict[str, Any]) -> BaseAgent:
        """Create agent instance"""
        agent_class = AgentRegistry.get(agent_id)
        if not agent_class:
            raise ValueError(f"Agent {agent_id} not found")
        
        agent = agent_class(config)
        
        # Validate configuration
        if not await agent.health_check():
            raise RuntimeError(f"Agent {agent_id} failed health check")
        
        return agent
```

### Phase 2: Agent Adapters (Week 2)

#### 2.1 LangGraph Adapter (Wrap Existing)
```python
# backend/app/agents/adapters/langgraph_adapter.py
from app.agents.base import BaseAgent, AgentResponse, AgentCapabilities
from app.agents.graph import run_agent, run_agent_streaming

class LangGraphAdapter(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Use existing LangGraph implementation
    
    async def execute(self, query: str, context: Dict[str, Any]) -> AgentResponse:
        # Wrap existing run_agent function
        state = await run_agent(
            user_query=query,
            tenant_id=context["tenant_id"],
            user_id=context["user_id"],
            session_id=context["session_id"]
        )
        
        return AgentResponse(
            answer=state.get("final_response"),
            citations=state.get("citations", []),
            metadata={"state": state},
            agent_id=self.agent_id,
            execution_time=0.0
        )
    
    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            supports_streaming=True,
            supports_tools=True,
            supports_memory=True,
            supports_multimodal=False,
            max_context_length=8000,
            supported_languages=["en"]
        )
```

#### 2.2 LangChain Adapter
```python
# backend/app/agents/adapters/langchain_adapter.py
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

class LangChainAdapter(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.llm = ChatOpenAI(model=config.get("model", "gpt-4"))
        self.tools = self._load_tools(config.get("tools", []))
        self.agent = self._create_agent()
    
    async def execute(self, query: str, context: Dict[str, Any]) -> AgentResponse:
        result = await self.agent.ainvoke({"input": query})
        
        return AgentResponse(
            answer=result["output"],
            citations=[],
            metadata={"intermediate_steps": result.get("intermediate_steps", [])},
            agent_id=self.agent_id,
            execution_time=0.0
        )
```

#### 2.3 n8n Adapter
```python
# backend/app/agents/adapters/n8n_adapter.py
import httpx

class N8NAdapter(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.webhook_url = config["webhook_url"]
        self.api_key = config.get("api_key")
    
    async def execute(self, query: str, context: Dict[str, Any]) -> AgentResponse:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.webhook_url,
                json={
                    "query": query,
                    "context": context
                },
                headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            )
            
            data = response.json()
            
            return AgentResponse(
                answer=data.get("answer", ""),
                citations=data.get("citations", []),
                metadata=data.get("metadata", {}),
                agent_id=self.agent_id,
                execution_time=0.0
            )
```

### Phase 3: Configuration System (Week 2)

#### 3.1 Agent Configuration Schema
```yaml
# backend/config/agents.yaml
agents:
  - id: "langgraph-default"
    name: "LangGraph RAG Agent"
    adapter: "langgraph"
    enabled: true
    priority: 1
    config:
      model: "gpt-4-turbo-preview"
      temperature: 0.7
      max_iterations: 10
  
  - id: "langchain-simple"
    name: "LangChain Simple Agent"
    adapter: "langchain"
    enabled: true
    priority: 2
    config:
      model: "gpt-3.5-turbo"
      tools: ["search", "calculator"]
  
  - id: "n8n-workflow"
    name: "n8n Custom Workflow"
    adapter: "n8n"
    enabled: false
    priority: 3
    config:
      webhook_url: "${N8N_WEBHOOK_URL}"
      api_key: "${N8N_API_KEY}"
  
  - id: "crewai-research"
    name: "CrewAI Research Team"
    adapter: "crewai"
    enabled: false
    priority: 4
    config:
      agents:
        - role: "researcher"
        - role: "writer"
```

#### 3.2 Configuration Loader
```python
# backend/app/agents/config_loader.py
import yaml
from pathlib import Path

class AgentConfigLoader:
    @staticmethod
    def load_config(config_path: str = "config/agents.yaml") -> Dict[str, Any]:
        """Load agent configurations from YAML"""
        path = Path(config_path)
        if not path.exists():
            return {"agents": []}
        
        with open(path) as f:
            config = yaml.safe_load(f)
        
        # Replace environment variables
        return AgentConfigLoader._replace_env_vars(config)
    
    @staticmethod
    def _replace_env_vars(config: Dict) -> Dict:
        """Replace ${VAR} with environment variables"""
        import os
        import re
        
        def replace(value):
            if isinstance(value, str):
                pattern = r'\$\{([^}]+)\}'
                return re.sub(pattern, lambda m: os.getenv(m.group(1), m.group(0)), value)
            elif isinstance(value, dict):
                return {k: replace(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [replace(item) for item in value]
            return value
        
        return replace(config)
```

### Phase 4: Unified API (Week 3)

#### 4.1 New API Endpoints
```python
# backend/app/api/agents_v2.py
from fastapi import APIRouter, Depends, HTTPException
from app.agents.orchestrator import AgentOrchestrator
from app.agents.factory import AgentFactory

router = APIRouter(prefix="/api/v2/agents")

@router.post("/execute")
async def execute_agent(
    request: AgentExecuteRequest,
    current_user: dict = Depends(get_current_user)
):
    """Execute any registered agent"""
    orchestrator = AgentOrchestrator()
    
    result = await orchestrator.execute(
        agent_id=request.agent_id or "default",
        query=request.query,
        context={
            "tenant_id": current_user["tenant_id"],
            "user_id": current_user["user_id"],
            "session_id": request.session_id
        }
    )
    
    return result

@router.get("/list")
async def list_agents():
    """List all available agents"""
    from app.agents.registry import AgentRegistry
    
    agents = []
    for agent_id in AgentRegistry.list_agents():
        agent_class = AgentRegistry.get(agent_id)
        # Get metadata
        agents.append({
            "id": agent_id,
            "name": agent_class.__name__,
            "capabilities": {}  # Add capabilities
        })
    
    return {"agents": agents}

@router.post("/compare")
async def compare_agents(
    request: CompareAgentsRequest,
    current_user: dict = Depends(get_current_user)
):
    """Execute same query on multiple agents and compare"""
    orchestrator = AgentOrchestrator()
    
    results = await orchestrator.execute_parallel(
        agent_ids=request.agent_ids,
        query=request.query,
        context={
            "tenant_id": current_user["tenant_id"],
            "user_id": current_user["user_id"]
        }
    )
    
    return {
        "query": request.query,
        "results": results,
        "comparison": orchestrator.compare_results(results)
    }
```

### Phase 5: Frontend Integration (Week 3)

#### 5.1 Agent Selector Component
```typescript
// src/components/agents/AgentSelector.tsx
export function AgentSelector() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string>('default');
  
  useEffect(() => {
    // Fetch available agents
    fetch('/api/v2/agents/list')
      .then(res => res.json())
      .then(data => setAgents(data.agents));
  }, []);
  
  return (
    <select value={selectedAgent} onChange={(e) => setSelectedAgent(e.target.value)}>
      {agents.map(agent => (
        <option key={agent.id} value={agent.id}>
          {agent.name}
        </option>
      ))}
    </select>
  );
}
```

---

## 📝 Configuration Examples

### Example 1: Using LangGraph (Default)
```env
AGENT_DEFAULT=langgraph-default
```

### Example 2: Using n8n Workflow
```env
AGENT_DEFAULT=n8n-workflow
N8N_WEBHOOK_URL=https://your-n8n.com/webhook/abc123
N8N_API_KEY=your-api-key
```

### Example 3: Using Multiple Agents
```yaml
agents:
  - id: "primary"
    adapter: "langgraph"
    enabled: true
  
  - id: "fallback"
    adapter: "langchain"
    enabled: true
```

---

## 🔌 Adding New Agent Frameworks

### Step-by-Step Guide

1. **Create Adapter Class**
```python
# backend/app/agents/adapters/your_adapter.py
from app.agents.base import BaseAgent

class YourAdapter(BaseAgent):
    async def execute(self, query, context):
        # Your implementation
        pass
```

2. **Register Adapter**
```python
# backend/app/agents/adapters/__init__.py
from app.agents.registry import AgentRegistry
from .your_adapter import YourAdapter

AgentRegistry.register("your-agent", YourAdapter)
```

3. **Add Configuration**
```yaml
# config/agents.yaml
agents:
  - id: "your-agent"
    adapter: "your-agent"
    config:
      # Your config
```

4. **Use It!**
```python
# No code changes needed - just configure!
```

---

## 📊 Benefits

### For Developers
- ✅ Add new agents without touching core code
- ✅ Test different frameworks easily
- ✅ Compare agent performance
- ✅ Gradual migration between frameworks

### For Users
- ✅ Choose best agent for their use case
- ✅ Switch agents without downtime
- ✅ Run multiple agents simultaneously
- ✅ Customize agent behavior via config

### For Operations
- ✅ Hot-reload configurations
- ✅ A/B test different agents
- ✅ Monitor agent performance
- ✅ Fallback mechanisms

---

## 🎯 Success Metrics

- **Extensibility:** Add new agent in < 1 hour
- **Performance:** < 5% overhead vs direct integration
- **Reliability:** 99.9% uptime with fallbacks
- **Usability:** Switch agents via config only

---

## 📅 Implementation Timeline

### Week 1: Core Infrastructure
- [ ] Base agent interface
- [ ] Agent registry
- [ ] Agent factory
- [ ] Configuration system

### Week 2: Adapters
- [ ] LangGraph adapter (wrap existing)
- [ ] LangChain adapter
- [ ] n8n adapter
- [ ] Documentation

### Week 3: API & Frontend
- [ ] Unified API endpoints
- [ ] Agent selector UI
- [ ] Comparison tools
- [ ] Testing & validation

### Week 4: Advanced Features
- [ ] Multi-agent orchestration
- [ ] Performance monitoring
- [ ] Agent marketplace
- [ ] Documentation & examples

---

## 🚀 Next Steps

1. **Review & Approve Plan**
2. **Setup Development Environment**
3. **Implement Core Infrastructure**
4. **Create Initial Adapters**
5. **Test & Iterate**
6. **Document & Deploy**

---

## 📚 Additional Resources

- LangChain Agents: https://python.langchain.com/docs/modules/agents/
- LangGraph: https://langchain-ai.github.io/langgraph/
- n8n Webhooks: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/
- CrewAI: https://github.com/joaomdmoura/crewAI
- AutoGen: https://microsoft.github.io/autogen/

---

**Ready to make your platform truly extensible! 🎉**
