## Relevant Files

- `src/modules/agent/simple_supervisor_agent.py` - The new supervisor agent to orchestrate the simplified workflow.
- `src/modules/agent/simple_rag_agent.py` - A new worker agent to wrap the existing RAG query engine.
- `src/modules/agent/simple_controller.py` - The new controller to manage the simplified agent system.
- `src/modules/query_answering/rag_chat_app.py` - The main Streamlit UI file that will be modified to use the new agent system.
- `src/modules/agent/action_extractor_agent.py` - Existing agent, will be used by the supervisor.
- `src/modules/agent/manual_checker_agent.py` - Existing agent, will be used by the supervisor.
- `src/modules/agent/query_refiner_agent.py` - Existing agent, will be used by the supervisor.

### Notes

- All new agent files should be created from scratch to ensure a clean implementation based on the PRD.

## Tasks

- [x] 1.0 Create New Agent Scaffolding
  - [x] 1.1 Create the file for the RAG worker: `src/modules/agent/simple_rag_agent.py`.
  - [x] 1.2 Implement the `SimpleRAGAgent` class within this file. It should initialize with a `MultimodalChromaRAGQueryEngine` instance.
  - [x] 1.3 Add a `process` method to the `SimpleRAGAgent` that accepts a query and other RAG parameters, executing the query and returning the results.

- [x] 2.0 Implement the Supervisor Agent Workflow
  - [x] 2.1 Create the file for the new supervisor: `src/modules/agent/simple_supervisor_agent.py`.
  - [x] 2.2 Implement the `SimpleSupervisorAgent` class. It should initialize all the required worker agents (`ActionExtractorAgent`, `ManualCheckerAgent`, `QueryRefinerAgent`, `SimpleRAGAgent`).
  - [x] 2.3 Implement the main `process_query` method as a generator. It should call the worker agents in the correct sequence (`ActionExtractor` -> `ManualChecker`).
  - [x] 2.4 The `process_query` method should `yield` the result of each step for UI display.
  - [x] 2.5 Implement the logic to handle when `ManualCheckerAgent` returns `manual_specified: false`. The supervisor should yield a `clarification_needed` state including the list of available manuals.
  - [x] 2.6 Implement a `resume_with_clarification` method that takes the user's selected manual, runs the `QueryRefinerAgent`, then the `SimpleRAGAgent`, and yields the final result.

- [x] 3.0 Develop a New Controller for the Simplified Workflow
  - [x] 3.1 Create the new controller file: `src/modules/agent/simple_controller.py`.
  - [x] 3.2 Implement a `SimpleAgentController` class to manage the lifecycle of the `SimpleSupervisorAgent`.
  - [x] 3.3 Add methods to the controller to create a session and to pass a user's query (and any clarification data) to the supervisor agent.

- [ ] 4.0 Integrate the New Agent System into the Streamlit UI
  - [ ] 4.1 In `src/modules/query_answering/rag_chat_app.py`, modify the `run_multi_agent_mode` function.
  - [ ] 4.2 Change the initialization from `AgentController` to the new `SimpleAgentController`.
  - [ ] 4.3 Adapt the agent processing loop to correctly iterate through the generator yielded by the new controller.
  - [ ] 4.4 Implement the UI for asking for clarification: when a `clarification_needed` step is received, display a dropdown of manuals for the user to select.
  - [ ] 4.5 Ensure the intermediate outputs from `ActionExtractorAgent`, `ManualCheckerAgent`, and `QueryRefinerAgent` are displayed correctly in the "View Agent Workflow" expander.
  - [ ] 4.6 Perform a test run of the "Simple RAG" mode to ensure no functionality has been broken during the changes.