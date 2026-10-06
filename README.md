Agent Simulation — Autonomous Multi-Agent System

A mobile-first autonomous multi-agent system designed to research, reason, plan, discover opportunities and operate tools while keeping Creator control over consequential real-world actions.

The system is evolving from a simple simulation into a persistent autonomous agent environment.

---

Core Principle

The agents are intended to be autonomous thinkers and workers, not autonomous authorities.

They can:

- perceive information
- research the web
- gather knowledge
- remember previous results
- analyse opportunities
- compare options
- create plans
- delegate work between agents
- monitor tasks
- propose actions
- prepare actions for execution
- learn from results
- continuously work toward objectives

However, when an action could have a consequential effect outside the agent system, the agent must stop at the Creator Approval Gate.

The Creator makes the final decision.

The rule

«Agents can propose. The Creator decides.»

An agent must not treat the existence of an objective as permission to perform consequential external actions.

---

Creator Approval System

Every protected consequential action is individually controlled.

The approval is tied to:

- the specific agent
- the specific tool
- the exact parameters
- the proposed action
- the approval request

An approval is consumed when execution begins and cannot be reused for another action.

This prevents an approval for one action from silently becoming permission for a different action.

Example

An agent proposes:

BUY
Item: Example Product
Seller: Example Seller
Price: £20
Quantity: 1

The Creator sees the proposal and can:

YES

or

NO

If approved, that exact approved action may execute.

If the agent later wants to buy:

Item: Example Product
Price: £40

it must create a new proposal and receive another Creator approval.

---

Autonomous Agent Loop

The intended autonomous operating cycle is:

PERCEIVE
   ↓
REMEMBER
   ↓
REASON
   ↓
PLAN
   ↓
SELECT TOOL
   ↓
CHECK SAFETY / PERMISSION
   ↓
   ┌───────────────────────────────┐
   │ Consequential external action │
   └───────────────────────────────┘
                  ↓
          Creator Approval
             YES / NO
                  ↓
              EXECUTE
                  ↓
             OBSERVE RESULT
                  ↓
                LEARN
                  ↓
               REPEAT

Agents should be able to continue working autonomously without requiring the Creator to approve every thought, search or internal calculation.

Creator intervention occurs at the action boundary, not at the reasoning boundary.

---

Operating Modes

SIMULATION

Simulation is the default and safest operating environment.

Agents can:

- research
- analyse
- create opportunities
- run simulated experiments
- move simulated resources
- test strategies
- interact with the simulated economy
- develop plans

No consequential real-world action is permitted from simulation mode.

---

LIVE

LIVE mode makes live-capable functionality available to the system.

LIVE does not mean unrestricted autonomy.

Protected consequential actions still require explicit Creator approval.

Examples include actions such as:

- purchasing something
- selling something
- spending money
- transferring money
- publishing external content
- posting to social media
- sending an external message
- executing a live commercial transaction
- creating or changing an external account
- taking another action with meaningful external consequences

The exact permission is determined by the tool's safety policy.

---

Creator-Controlled Action Gate

The intended architecture is:

Creator
   │
   │ YES / NO
   ▼
Approval Gate
   │
   ▼
Agent Orchestrator
   │
   ├── Cognitive Room
   ├── Memory
   ├── Brain / Reasoning
   └── Tool Registry
            │
            ▼
      External Services

The Approval Gate is therefore a security boundary between autonomous reasoning and consequential execution.

---

Current Agents

Boss

The Boss is the primary coordinator.

Responsibilities include:

- receiving Creator objectives
- coordinating other agents
- assigning tasks
- monitoring system state
- requesting reports
- delegating research
- coordinating opportunity discovery
- coordinating economic analysis

The Boss does not automatically receive permission to perform consequential external actions.

---

Banker

The Banker is responsible for financial state and accounting.

Responsibilities include:

- balances
- transactions
- financial reporting
- economic state
- financial records
- monitoring simulated economic activity

The Banker is intended to remain the financial authority inside the agent system.

---

InfoFarmer

The InfoFarmer is the research and intelligence specialist.

Responsibilities include:

- web research
- information gathering
- knowledge storage
- source collection
- research requests
- supplying information to other agents

Public research can operate autonomously.

Research does not itself grant permission to perform a consequential action.

---

OpportunityAgent

The OpportunityAgent searches for and evaluates potential opportunities.

Responsibilities include:

- discovering opportunities
- analysing costs
- estimating potential revenue
- calculating potential profit
- estimating ROI
- assessing risk
- proposing experiments
- monitoring experiment results

A profitable-looking opportunity is not automatically permission to act on it.

---

Cognitive Rooms

Each agent has a private "CognitiveRoom".

The Cognitive Room separates the agent's internal cognitive state from the shared system state.

It stores information such as:

- identity
- objectives
- memories
- observations
- thoughts
- messages
- plans
- current status

This provides the foundation for more advanced autonomous reasoning.

---

Shared Memory

The system maintains persistent shared memory containing:

- world state
- agent status
- knowledge
- tasks
- transactions
- logs
- Creator approvals
- economic state

The intention is for agents to build on previous work instead of starting from zero after every cycle.

---

Tool System

Agents interact with the world through registered tools.

Tools have defined capabilities and safety properties.

A tool can be:

- simulation-safe
- live-capable
- Creator-protected
- research-only
- internal
- external

The Tool Registry is responsible for enforcing the execution rules rather than allowing individual agents to bypass them.

---

Research

The current research layer provides web research functionality using public web information sources.

The system can:

1. search
2. collect results
3. read pages
4. store useful information
5. return findings to agents

The research system will be expanded over time to support broader information sources and more sophisticated intelligence gathering.

---

Economy

The economy supports:

- opportunities
- opportunity analysis
- simulated experiments
- revenue
- expenses
- profit
- ROI
- risk classification
- economic reporting

The current system supports both:

SIMULATION
REAL

with protected live actions remaining subject to Creator approval.

---

Social Media and External Services

The long-term system may allow agents to work with external services where appropriate APIs, permissions and platform rules permit it.

For example, an agent may eventually be able to:

Research a topic
      ↓
Develop a content idea
      ↓
Draft an Instagram post
      ↓
Present the proposed post to Creator
      ↓
Creator: YES
      ↓
Publish

The agent should not silently publish because it was given a general objective such as:

«"Make money from Instagram."»

The objective authorises the agent to work toward the goal.

It does not constitute blanket permission to publish, spend money or perform other consequential actions.

---

Revenue and Opportunity Development

One of the long-term goals of the project is to allow agents to autonomously discover legitimate opportunities for generating revenue.

The intended process is:

Research
   ↓
Identify opportunity
   ↓
Analyse
   ↓
Estimate costs
   ↓
Estimate revenue
   ↓
Assess risk
   ↓
Create proposal
   ↓
Creator decision
   ↓
Execute approved action
   ↓
Measure result
   ↓
Learn
   ↓
Improve next proposal

The system should favour legitimate, transparent and platform-compliant opportunities.

The agents should not bypass platform restrictions, payment controls, account security or other safeguards.

---

Safety Model

The system follows a simple distinction:

Autonomous cognition

Agents may generally:

- think
- research
- analyse
- plan
- compare
- remember
- communicate internally
- simulate
- propose

Creator-controlled execution

Consequential external actions require explicit approval.

This separation is fundamental to the architecture.

---

Project Structure

agent-simulation/
│
├── agents/
│   ├── base_agent.py
│   ├── boss.py
│   ├── banker.py
│   ├── info_farmer.py
│   └── opportunity_agent.py
│
├── core/
│   ├── approvals.py
│   ├── cognitive_room.py
│   ├── economy.py
│   ├── memory.py
│   ├── research.py
│   ├── tools.py
│   └── world.py
│
├── data/
│   └── memory.json
│
├── modules/
│
├── ui/
│
├── main.py
├── requirements.txt
├── Procfile
└── runtime.txt

---

Current Development Direction

The project is being developed toward:

Phase 1 — Autonomous Core

- persistent memory
- Cognitive Rooms
- multiple agents
- task delegation
- autonomous research
- opportunity analysis
- simulation economy
- Creator Approval Gate

Phase 2 — Autonomous Orchestration

- continuous agent cycles
- automatic task processing
- agent-to-agent communication
- objectives
- planning
- observation
- learning from results
- improved reasoning

Phase 3 — External Tools

- broader web research
- APIs
- approved external services
- social platforms where permitted
- external data sources
- commercial tools

Phase 4 — Controlled Real-World Execution

Live-capable tools can be introduced behind the Creator Approval Gate.

The objective is not unrestricted autonomy.

The objective is:

«Autonomous intelligence with controlled real-world execution.»

Phase 5 — Continuous Operation

The system can eventually run continuously in the cloud, maintaining:

- memory
- objectives
- tasks
- research
- opportunity discovery
- proposals
- approval requests
- results
- learning

while keeping the Creator as the final authority over consequential actions.

---

Running the Application

Install dependencies:

pip install -r requirements.txt

Start the server:

python main.py

or:

uvicorn main:app --host 0.0.0.0 --port 8000

Then open:

http://localhost:8000

For cloud deployment, the application can be hosted on a compatible Python service such as Render.

---

Development Philosophy

This project is deliberately modular.

The goal is to build the autonomous system in layers:

Memory
   ↓
Cognition
   ↓
Agents
   ↓
Tools
   ↓
Orchestration
   ↓
Research
   ↓
Opportunity Discovery
   ↓
Creator Approval
   ↓
External Execution
   ↓
Learning

Each layer should have a clear responsibility.

Most importantly:

«The agents should be capable of working autonomously, but autonomy is not the same thing as unrestricted authority.»

The Creator remains the final decision-maker for consequential external actions.

---

Project Status

Active development

The current repository is being transitioned from the original Module 1 simulation into the autonomous multi-agent architecture described above.
