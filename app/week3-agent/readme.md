🟨 Agent — Minimum Viable Architecture
Part	Minimum value	What it does
🧠 LLM	Reasoning/decision	Decides what should happen next
🛠️ Tools	Action	Lets the agent interact with the outside world
📋 Tool Schema	Contract	Defines tool name, arguments, and types
🔄 Agent Loop	Iteration	observe → decide → act → observe
🧠 State	Continuity	Keeps current task/conversation/tool state
🛡️ Validation	Safety	Checks tool arguments before execution
⚡ Executor	Real-world effect	Application actually executes the tool
📤 Tool Result	Feedback	Gives execution result back to the LLM
🛑 Termination	Control	Knows when the task is finished
The absolute core
                 ┌──────────────┐
                 │     LLM      │
                 │ decide next  │
                 └──────┬───────┘
                        │
                   tool request
                        ↓
                 ┌──────────────┐
                 │  VALIDATOR   │
                 └──────┬───────┘
                        ↓
                 ┌──────────────┐
                 │    TOOL      │
                 │   EXECUTOR   │
                 └──────┬───────┘
                        │
                    result
                        ↓
                 ┌──────────────┐
                 │     LLM      │
                 └──────────────┘
                        ↻
Minimum definition:

An agent is an LLM-driven loop that can observe state, decide an action, call an authorized tool, receive the result, and continue until a termination condition is reached.
