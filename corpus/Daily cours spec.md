# 8-Week AI Engineer Upgrade — Daily Course Generation Specification

## Purpose

This file is the **source of truth for generating the full lesson for any day** of the 8-week AI Engineer upgrade.

When generating `Day N of Week M`, use the corresponding day specification below and produce a complete practical lesson.

The original 8-week plan targets a transition from Full-Stack Developer toward AI Engineer / AI Application Engineer / GenAI Engineer / LLM Engineer / Agentic AI Engineer.

**Time:** 2–3 hours/day, 6 days/week
**Learning ratio:** 70% building, 20% learning, 10% theory.

---

# Global Rules for Every Day

Every generated daily course must contain:

1. **Day objective**
2. **Why this matters for an AI Engineer**
3. **Prerequisites / connection to previous days**
4. **Theory**
   - Explain the concepts from first principles.
   - Explain the engineering mental model.
   - Explain important terminology.
5. **Architecture / flow**
   - Use diagrams when useful.
   - Show where the concept sits in a real AI system.
6. **Code**
   - Prefer Python for AI/backend concepts.
   - Use TypeScript/Node.js where relevant to the user's full-stack background.
   - Do not hide important mechanics behind frameworks.
   - Explain the code.
7. **Hands-on implementation**
   - Build something that actually works.
8. **Exercise**
   - Give a concrete task to implement independently.
9. **Mini-project / integration**
   - Connect the day's concept to the week's project.
10. **Mini-test**
    - Conceptual + practical questions.
    - Include answers only after the questions or in a separate answer section.
11. **Interview questions**
    - Include realistic AI Engineer interview questions.
12. **Definition of Done**
    - A checklist of skills the learner should be able to demonstrate.
13. **Common mistakes**
14. **Production notes**
    - Reliability, security, cost, observability, scalability, or architecture where relevant.
15. **Next-day bridge**
    - Explain what today's work enables tomorrow.

## Teaching Style

- Practical and engineering-oriented.
- First principles before abstractions/frameworks.
- 70% building, 20% learning, 10% theory.
- Avoid unnecessary mathematical proofs.
- Explain *why*, not just *how*.
- Use progressively harder examples.
- Favor small runnable examples before the final implementation.
- Explicitly distinguish prototype shortcuts from production approaches.
- The learner should finish each day with something they can put on GitHub or discuss in an interview.

## Standard Daily Timebox

Target approximately:

- 15–25 min: theory
- 20–30 min: guided code
- 60–90 min: hands-on building
- 20–30 min: exercise
- 10–15 min: mini-test/interview questions
- 5–10 min: review + Definition of Done

---

# Week 1 — Python + LLM APIs

## Week Goal

Become comfortable enough with Python to build AI backends.

Topics from the master plan:

- Python syntax/data structures
- Virtual environments
- Type hints
- async/await
- Pydantic
- FastAPI
- REST APIs
- Environment variables
- OpenAI / Anthropic / Gemini APIs
- Streaming
- Structured JSON outputs

## Week Project

### Project #1 — AI API

Architecture:

```text
React / Next.js
      ↓
   FastAPI
      ↓
   LLM API
      ↓
Structured response
```

Implement:

- Chat
- Streaming
- Structured output
- Error handling
- Token/cost tracking

Target capability:

> “I can integrate an LLM into an existing production application.”

---

## Day 1 — Python for AI Engineering

### Must contain

- Python mental model for a JavaScript/TypeScript developer
- Variables and types
- Lists, tuples, sets, dictionaries
- Functions
- Control flow
- Comprehensions
- Modules/imports
- Exceptions
- Basic file handling
- `pip`
- Virtual environments
- Running Python programs

### Build

Create a small CLI/text-processing program.

### Exercise

Build a Python program that accepts text and returns useful statistics.

### Mini-test

Cover Python syntax, data structures, mutability, exceptions, imports, and virtual environments.

### Definition of Done

- Can write basic Python without copying syntax.
- Can create/use a virtual environment.
- Can manipulate common data structures.
- Can structure a small Python module.

---

## Day 2 — Type Hints + Pydantic

### Must contain

- Why dynamic Python benefits from typing
- Type hints
- `Optional`
- `Union` / modern union syntax
- `list`, `dict`, `Literal`
- Dataclasses
- Pydantic models
- Validation
- Serialization/deserialization
- Why structured data matters for LLM applications

### Build

Define typed request/response models for an AI API.

### Exercise

Create validated models for a chat request and structured AI response.

### Mini-test

Explain type hints vs runtime validation and why Pydantic is useful around APIs/LLMs.

### Definition of Done

- Can type Python functions.
- Can define Pydantic models.
- Can validate incoming data.
- Can serialize validated data.

---

## Day 3 — Async/Await + HTTP

### Must contain

- Synchronous vs asynchronous execution
- `async`
- `await`
- Event loop mental model
- I/O-bound work
- HTTP clients
- Concurrent API calls
- When async helps and when it does not

### Build

Call an HTTP API asynchronously.

### Exercise

Implement multiple concurrent requests and compare sequential vs concurrent execution.

### Mini-test

Explain why LLM/API calls are good candidates for async I/O.

### Definition of Done

- Understand async/await.
- Can make async HTTP requests.
- Can explain concurrency vs parallelism.
- Can identify I/O-bound workloads.

---

## Day 4 — FastAPI + REST APIs

### Must contain

- FastAPI mental model
- Routes
- HTTP methods
- Request/response lifecycle
- Pydantic request models
- Response models
- Status codes
- Dependency injection basics
- API error handling
- OpenAPI documentation

### Build

Create the AI API skeleton.

### Exercise

Create endpoints such as:

```text
POST /chat
GET /health
```

### Mini-test

Explain REST, HTTP status codes, request validation, and response schemas.

### Definition of Done

- Can create a FastAPI service.
- Can define typed endpoints.
- Can validate requests.
- Can return structured responses.

---

## Day 5 — LLM APIs + Streaming

### Must contain

- LLM API request/response model
- Messages/prompts
- System/user/assistant roles
- Temperature concept
- Token usage
- API errors
- Timeouts
- Retries
- Streaming
- Server-Sent Events or equivalent streaming mechanism
- Provider abstraction concept

### Build

Connect FastAPI to an LLM provider.

Implement:

```text
POST /chat
     ↓
LLM API
     ↓
response
```

Then add streaming.

### Exercise

Add provider-independent `LLMClient` abstraction.

### Mini-test

Explain tokens, streaming, timeouts, retries, and why provider calls should be isolated behind an adapter.

### Definition of Done

- Can call an LLM from Python.
- Can stream output.
- Can handle API failures.
- Understands basic token/cost implications.

---

## Day 6 — Structured Outputs + Project #1

### Must contain

- Structured JSON output
- Schema-constrained generation
- Validation
- LLM output failure handling
- Token/cost tracking
- Production error handling
- Final architecture review

### Build

Complete Project #1:

```text
React / Next.js
      ↓
FastAPI
      ↓
LLM adapter
      ↓
Structured response
```

### Exercise

Add:

- Chat
- Streaming
- Structured output
- Error handling
- Cost tracking

### Mini-test

Architecture and interview questions covering the entire week.

### Definition of Done

- Project runs end-to-end.
- LLM output is structured and validated.
- Streaming works.
- Errors are handled.
- Usage/cost is measurable.
- Can explain the architecture in an interview.

---

# Week 2 — RAG

## Week Goal

Understand and build Retrieval-Augmented Generation rather than merely hiding the system behind a framework.

Topics:

- Embeddings
- Vector databases
- Chunking
- Metadata
- Similarity search
- Hybrid search
- Retrieval
- Reranking
- Context construction
- Citations
- RAG evaluation

## Week Project

### AI Knowledge Assistant

Accept:

- PDF
- DOCX
- TXT
- Web pages

Pipeline:

```text
Documents
    ↓
Parsing
    ↓
Chunking
    ↓
Embeddings
    ↓
Vector DB
    ↓
Retriever
    ↓
LLM
    ↓
Answer + Sources
```

Suggested storage:

- PostgreSQL + pgvector
- or Qdrant

Important:

> Understand what happens underneath. Do not simply use LangChain and call it RAG.

---

## Day 1 — Embeddings + Semantic Search

### Must contain

- What RAG solves
- RAG pipeline
- Embeddings
- Vector representations
- Semantic similarity
- Cosine similarity
- Similarity search
- Query vs document embeddings
- Indexing-time vs query-time processing
- Why keyword search alone can fail

### Build

First implement cosine similarity manually.

Then build a tiny semantic search engine without LangChain.

### Exercise

Create a small corpus and rank documents by semantic similarity.

### Mini-test

Explain:

- What an embedding is
- Why embeddings enable semantic search
- Cosine similarity
- Embedding vs retrieval

### Definition of Done

- Can explain RAG.
- Can explain embeddings.
- Can calculate cosine similarity.
- Can build basic semantic retrieval.
- Understands indexing vs querying.

---

## Day 2 — Document Ingestion + Chunking

### Must contain

- Why documents are chunked
- Chunk size
- Chunk overlap
- Context preservation
- Paragraph/section-based splitting
- Why naive character splitting can be poor
- Document representation
- Chunk representation
- Metadata
- Why metadata matters
- Ingestion pipeline

### Build

Implement:

```text
Document
  ↓
Parse
  ↓
Clean
  ↓
Split
  ↓
Chunks
  ↓
Metadata
```

Use Python dataclasses or Pydantic models.

### Exercise

Build a chunker supporting overlap and metadata.

### Mini-test

Explain chunks, overlap, logical sections, metadata, and chunk quality.

### Definition of Done

- Can implement basic chunking.
- Can implement overlap.
- Can split logical sections.
- Can represent documents and chunks.
- Can attach metadata.
- Can explain how chunk quality affects retrieval.

---

## Day 3 — Vector Database + Real Embeddings

### Must contain

- Vector database mental model
- Vector indexing
- Storing embeddings
- IDs and metadata
- Similarity queries
- Top-k retrieval
- PostgreSQL + pgvector or Qdrant
- Embedding model/API
- Distance metrics
- Retrieval tradeoffs

### Build

Store chunks and embeddings in a vector store.

Implement:

```text
query
 ↓
embedding
 ↓
vector search
 ↓
top-k chunks
```

### Exercise

Add filtering by metadata.

### Mini-test

Explain vector DBs, top-k, metadata filtering, and why vector storage is different from ordinary relational search.

### Definition of Done

- Can generate real embeddings.
- Can store vectors.
- Can retrieve top-k chunks.
- Can use metadata filters.
- Can explain the retrieval layer.

---

## Day 4 — Build the Real RAG Pipeline

### Must contain

- Full RAG flow
- Query embedding
- Retrieval
- Context construction
- Prompt construction
- LLM generation
- Grounding
- Context limits
- Relevant vs irrelevant context
- Basic citation source tracking

### Build

Implement:

```text
Question
   ↓
Embedding
   ↓
Retriever
   ↓
Top-k chunks
   ↓
Context builder
   ↓
Prompt
   ↓
LLM
   ↓
Answer
```

### Exercise

Create a `/ask` endpoint for the Knowledge Assistant.

### Mini-test

Explain each stage and what can go wrong.

### Definition of Done

- End-to-end RAG works.
- Retrieved chunks are passed to the LLM.
- The answer is grounded in retrieved context.
- Sources can be associated with retrieved chunks.

---

## Day 5 — Hybrid Search + Reranking + Citations

### Must contain

- Keyword/BM25-style retrieval
- Vector retrieval
- Hybrid search
- Why hybrid search can outperform either alone
- Reranking
- Candidate retrieval vs final ranking
- Citation generation
- Source metadata
- Context ordering

### Build

Implement:

```text
Query
 ├── Vector search
 └── Keyword search
        ↓
   Candidate set
        ↓
     Reranker
        ↓
   Final context
        ↓
       LLM
        ↓
   Answer + Sources
```

### Exercise

Compare vector-only vs hybrid retrieval.

### Mini-test

Explain recall vs precision in retrieval, reranking, and citations.

### Definition of Done

- Can explain hybrid retrieval.
- Can implement a basic hybrid strategy.
- Understands reranking.
- Can attach citations/sources to answers.

---

## Day 6 — RAG Evaluation + Project Completion

### Must contain

- Retrieval quality
- Answer quality
- Faithfulness
- Relevance
- Groundedness
- Basic evaluation dataset
- Failure analysis
- Retrieval debugging
- RAG observability
- Production considerations

### Build

Finish the AI Knowledge Assistant.

Test questions should measure:

- Retrieval success
- Correct answer
- Wrong context
- Missing context
- Hallucination

### Exercise

Create a small evaluation dataset and score the system.

### Mini-test

Full RAG interview test.

### Definition of Done

- Knowledge Assistant accepts target document types.
- Ingestion works.
- Chunking works.
- Embeddings work.
- Vector retrieval works.
- RAG works.
- Citations work.
- Basic evaluation exists.
- Can explain the entire RAG pipeline without relying on a framework abstraction.

---

# Week 3 — Agents

## Week Goal

Build reliable tool-using agents rather than toy chatbots.

Topics:

- Tool/function calling
- Agent loops
- State
- Memory
- Planning
- Tool selection
- Single-agent vs multi-agent
- Human approval
- Retries
- Timeouts
- Idempotency
- MCP

## Week Project

### Project #2 — AI Operations Agent

Tools:

```text
search_web()
search_documents()
get_customer()
create_ticket()
send_email()
update_database()
```

Architecture:

```text
             ┌── Web Search
             │
User → Agent ├── Database
             │
             ├── RAG
             │
             └── External API
```

Build something resembling an enterprise system, not a toy agent.

---

## Day 1 — Tool Calling / Function Calling

### Must contain

- What an agent is
- Tool calling vs normal LLM generation
- Tool schemas
- Function definitions
- Tool arguments
- Tool results
- Validation
- Tool execution boundaries

### Build

Implement a model that can choose from simple tools.

### Exercise

Create:

```text
get_customer()
search_documents()
```

### Definition of Done

- Understands tool calling.
- Can define tool schemas.
- Can execute validated tool calls.
- Can distinguish model decision from tool execution.

---

## Day 2 — Agent Loop + State

### Must contain

- Agent loop
- Observe → decide → act → observe
- State
- Conversation state
- Tool state
- Termination
- Maximum iterations
- Failure handling

### Build

Create a basic agent loop without an agent framework.

### Exercise

Add iteration limits and structured state.

### Definition of Done

- Can implement a basic agent loop.
- Understands state.
- Prevents infinite loops.

---

## Day 3 — Memory + Planning + Tool Selection

### Must contain

- Short-term memory
- Long-term memory concept
- Planning
- Replanning
- Tool selection
- Tool descriptions
- Single-agent vs multi-agent tradeoffs

### Build

Add memory and a simple planning strategy.

### Exercise

Make the agent choose the minimum necessary tools.

### Definition of Done

- Can explain memory types.
- Can explain planning.
- Can justify single vs multi-agent architecture.

---

## Day 4 — Reliability: Retries, Timeouts, Idempotency

### Must contain

- Timeouts
- Retries
- Exponential backoff
- Retryable vs non-retryable errors
- Idempotency
- Duplicate side effects
- Safe tool execution
- Circuit-breaker concept

### Build

Make agent tools retry-safe.

### Exercise

Implement idempotency for `create_ticket()`.

### Definition of Done

- Can design retry-safe tools.
- Understands idempotency.
- Can prevent duplicate side effects.

---

## Day 5 — Human Approval + MCP

### Must contain

- Human-in-the-loop
- Approval boundaries
- High-risk actions
- MCP concept
- MCP servers/tools/resources at a conceptual and practical level
- Security boundaries

### Build

Add approval before an external side effect.

### Exercise

Require approval before:

```text
send_email()
update_database()
```

### Definition of Done

- Can identify actions requiring approval.
- Understands MCP.
- Can design safe tool boundaries.

---

## Day 6 — AI Operations Agent

### Must contain

- Full architecture review
- Tool registry
- Agent loop
- State
- Memory
- RAG integration
- Reliability
- Human approval
- Logging
- Final project

### Build

Complete Project #2.

### Definition of Done

- Agent uses multiple tools.
- Agent can use RAG.
- State is controlled.
- Retries/timeouts exist.
- Side effects are protected.
- Human approval exists where appropriate.
- Can explain architecture in an interview.

---

# Week 4 — AI Evaluation

## Week Goal

Learn to measure AI systems instead of assuming they work.

Topics:

- Hallucination measurement
- Correctness
- Relevance
- Faithfulness
- Retrieval quality
- Latency
- Token usage
- Cost
- Regression testing
- LLM-as-judge
- Test datasets

## Week Project

Build an evaluation pipeline using approximately 100 questions.

Architecture:

```text
100 questions
      ↓
AI system
      ↓
Answers
      ↓
Evaluator
      ↓
Scores
```

Dashboard metrics:

- Answer accuracy
- Retrieval accuracy
- Hallucination rate
- Average latency
- Cost/request

---

## Day 1 — AI Evaluation Mental Model

### Must contain

- Why AI systems need evaluation
- Traditional software tests vs AI evaluation
- Test cases
- Ground truth
- Reference answers
- Evaluation dimensions

### Build

Create an initial evaluation dataset.

---

## Day 2 — Retrieval Evaluation

### Must contain

- Retrieval correctness
- Precision
- Recall
- Top-k
- Hit rate
- Context relevance
- Retrieval failure analysis

### Build

Evaluate the RAG retriever independently from the LLM.

---

## Day 3 — Answer Quality

### Must contain

- Correctness
- Relevance
- Faithfulness
- Groundedness
- Hallucination
- Reference-answer comparison

### Build

Score generated answers.

---

## Day 4 — LLM-as-Judge

### Must contain

- LLM-as-judge
- Rubrics
- Structured evaluation
- Judge bias
- Agreement with humans
- When not to trust the judge

### Build

Create a structured judge.

---

## Day 5 — Regression + Cost + Latency

### Must contain

- Regression datasets
- Golden tests
- Latency measurement
- Token usage
- Cost/request
- Performance baselines

### Build

Run evaluations automatically and store results.

---

## Day 6 — Evaluation Dashboard

### Must contain

- Metric aggregation
- Trends
- Failure categories
- Regression detection
- Final evaluation report

### Build

Complete the evaluation pipeline/dashboard.

### Definition of Done

- Has a real test dataset.
- Measures retrieval quality.
- Measures answer quality.
- Measures hallucination/faithfulness.
- Measures latency.
- Measures cost.
- Can detect regressions.

---

# Week 5 — ML Fundamentals + PyTorch

## Week Goal

Build engineering intuition for ML and deep learning.

### Classical ML

- Regression
- Classification
- Clustering
- Train/validation/test
- Overfitting
- Regularization
- Precision
- Recall
- F1
- ROC-AUC

### Deep Learning

```text
Tensor
   ↓
Neural Network
   ↓
Loss
   ↓
Backpropagation
   ↓
Optimizer
   ↓
Training
```

### PyTorch

- Tensors
- Datasets
- Dataloaders
- Training loops
- Inference

Focus on engineering intuition, not mathematical proofs.

---

## Day 1 — ML Mental Model + Data

### Must contain

- What machine learning is
- Features
- Labels
- Training
- Inference
- Dataset splitting
- Leakage
- Baselines

### Build

Train a simple model on a small dataset.

---

## Day 2 — Regression + Classification

### Must contain

- Regression
- Classification
- Decision boundaries
- Loss
- Basic model training

### Build

Train and compare simple models.

---

## Day 3 — Evaluation + Overfitting

### Must contain

- Train/validation/test
- Overfitting
- Underfitting
- Regularization
- Precision
- Recall
- F1
- ROC-AUC

### Build

Demonstrate overfitting and mitigation.

---

## Day 4 — Neural Networks

### Must contain

- Neurons
- Layers
- Activation functions
- Forward pass
- Loss
- Backpropagation
- Optimizers

### Build

Implement/train a small neural network.

---

## Day 5 — PyTorch Fundamentals

### Must contain

- Tensors
- Shapes
- Datasets
- Dataloaders
- Modules
- Optimizers
- Training loops

### Build

Train a PyTorch model.

---

## Day 6 — Training + Inference Pipeline

### Must contain

- Complete training loop
- Validation
- Checkpoints
- Inference
- Basic experiment tracking concepts

### Build

Complete a small PyTorch project.

### Definition of Done

- Can explain the ML lifecycle.
- Understands overfitting.
- Can interpret core classification metrics.
- Can build a basic PyTorch training loop.
- Can perform inference.

---

# Week 6 — Production AI / MLOps

## Week Goal

Learn how to deploy and operate production AI systems.

Topics:

- Docker
- CI/CD
- Cloud deployment
- Model/API serving
- Logging
- Monitoring
- Tracing
- Queues
- Caching
- Rate limiting
- Retries
- Circuit breakers
- Secrets
- Authentication
- Authorization

## Target Architecture

```text
React / Next.js
      ↓
API Gateway
      ↓
AI Service
      ↓
Agent
 ├── RAG
 ├── Tools
 └── LLM
      ↓
PostgreSQL

Queue
  ↓
Worker
```

Containerize and deploy it.

---

## Day 1 — Docker for AI Applications

### Must contain

- Containers
- Images
- Dockerfile
- Environment variables
- Volumes
- Networks
- Multi-stage builds
- Containerizing FastAPI/AI service

### Build

Dockerize an AI backend.

---

## Day 2 — CI/CD

### Must contain

- CI vs CD
- GitHub Actions
- Linting
- Tests
- Build
- Deployment pipeline
- Secrets

### Build

Create a CI pipeline.

---

## Day 3 — Cloud Deployment + Serving

### Must contain

- Deployment architecture
- API serving
- Environment configuration
- Health checks
- Horizontal scaling concept
- Model/API provider separation

### Build

Deploy the service using a practical low-cost/free approach.

---

## Day 4 — Observability

### Must contain

- Structured logging
- Metrics
- Tracing
- Correlation IDs
- AI-specific telemetry
- Token/cost monitoring
- Latency

### Build

Instrument the AI service.

---

## Day 5 — Reliability + Performance

### Must contain

- Queues
- Workers
- Caching
- Rate limiting
- Retries
- Circuit breakers
- Backpressure
- Async jobs

### Build

Move a long-running AI task into a worker.

---

## Day 6 — Security + Production Architecture

### Must contain

- Authentication
- Authorization
- Secrets
- API security
- Input validation
- Abuse protection
- Production architecture review

### Build

Integrate the week's concepts into a production-style AI architecture.

### Definition of Done

- AI service is containerized.
- CI/CD exists.
- Deployment works.
- Logs/metrics exist.
- Long-running work can use a worker.
- Rate limiting/retries are understood.
- Authentication/authorization boundaries are defined.

---

# Week 7 — Advanced AI Engineering

## Week Goal

Understand the internals and security of modern AI systems.

### LLM Architecture

- Transformer basics
- Attention
- Context windows
- Tokenization
- Inference
- Temperature
- Sampling
- Quantization
- Fine-tuning vs RAG
- LoRA / QLoRA concepts

### AI Security

- Prompt injection
- Data leakage
- Malicious documents
- Excessive agent permissions
- Tool abuse
- PII
- Access control

### Advanced Agent Architecture

```text
User
  ↓
Router
  ↓
Agent
 ├── RAG
 ├── Tools
 ├── Memory
 └── Sub-agents
  ↓
Validator
  ↓
Human approval
  ↓
Action
```

---

## Day 1 — Transformers + Attention

### Must contain

- Transformer mental model
- Tokens
- Embeddings
- Attention
- Self-attention
- Query/key/value intuition
- Why transformers work well for language

### Build

Implement a tiny attention mechanism or inspect one programmatically.

---

## Day 2 — Context, Tokenization + Inference

### Must contain

- Context windows
- Tokenization
- Input/output tokens
- Inference
- Temperature
- Sampling
- Deterministic vs stochastic generation

### Build

Experiment with generation parameters and token counts.

---

## Day 3 — Quantization + Model Serving

### Must contain

- Model size
- Precision
- Quantization
- Memory implications
- Inference speed
- Local vs hosted models

### Build

Run or inspect a quantized local model if hardware allows.

---

## Day 4 — RAG vs Fine-Tuning + LoRA/QLoRA

### Must contain

- When to use RAG
- When to fine-tune
- Fine-tuning mental model
- LoRA
- QLoRA
- Knowledge vs behavior adaptation

### Exercise

Given several product requirements, choose RAG, fine-tuning, prompt engineering, or a combination.

---

## Day 5 — AI Security

### Must contain

- Prompt injection
- Indirect prompt injection
- Data leakage
- Malicious documents
- Tool abuse
- Excessive permissions
- PII
- Access control
- Output validation

### Build

Create attacks against a toy agent and then mitigate them.

---

## Day 6 — Advanced Agent Architecture

### Must contain

- Router
- Agent
- RAG
- Tools
- Memory
- Validators
- Human approval
- Security boundaries
- Final architecture review

### Build

Upgrade Project #2 toward the advanced architecture.

### Definition of Done

- Can explain transformer/attention intuition.
- Understands context and tokenization.
- Understands sampling.
- Can explain quantization.
- Can choose RAG vs fine-tuning.
- Can identify major AI security risks.
- Can design a guarded agent architecture.

---

# Week 8 — Portfolio + Interviews

## Week Goal

Do **not** focus on new technologies. Package the work and become interview-ready.

## Project 1 — RAG Enterprise Assistant

Features:

- Document ingestion
- Embeddings
- Vector search
- Citations
- RAG
- Evaluation
- Authentication
- Monitoring

## Project 2 — Autonomous Business Agent

Flow:

```text
Customer request
      ↓
Knowledge search
      ↓
Customer lookup
      ↓
Issue determination
      ↓
Create ticket
      ↓
Draft response
      ↓
Human approval
      ↓
Send response
```

## Project 3 — AI Production Platform

Suggested stack:

```text
React / Next.js
TypeScript
Node.js
Python
FastAPI
PostgreSQL
Redis
Queue
Docker
LLM
RAG
Agent
Evaluation
CI/CD
Cloud
Observability
```

This is the flagship portfolio project.

---

## Day 1 — Portfolio Architecture Review

### Must contain

- Review all three projects
- Identify architecture weaknesses
- Clean dependency boundaries
- README requirements
- Architecture diagrams
- Tradeoff documentation

### Build

Create production-quality README/architecture documentation.

---

## Day 2 — Testing + Quality

### Must contain

- Unit tests
- Integration tests
- API tests
- E2E tests
- RAG evaluation tests
- Agent behavior tests
- Regression tests

### Build

Create a meaningful test suite across the projects.

---

## Day 3 — Observability + Production Hardening

### Must contain

- Logging
- Metrics
- Tracing
- Error handling
- Security review
- Cost controls
- Rate limits
- Retry behavior

### Build

Harden the flagship project.

---

## Day 4 — CV + GitHub Portfolio

### Must contain

- AI Engineer positioning
- Project descriptions
- Technical impact
- Architecture bullets
- Metrics
- GitHub README quality
- What to demonstrate in interviews

Target profile:

> Full-Stack / AI Engineer — TypeScript, Node.js, Python, LLMs, RAG, Agents, AI Systems & MLOps

### Build

Rewrite project descriptions into interview/CV-ready evidence.

---

## Day 5 — AI Engineer Interview Day

### Must contain

Technical questions covering:

- LLM APIs
- RAG
- Embeddings
- Vector DBs
- Agents
- Tool calling
- Evaluation
- Python/FastAPI
- PostgreSQL
- Docker
- Cloud
- MLOps
- Security
- System design

### Exercise

Conduct a simulated technical interview.

---

## Day 6 — Final Capstone + System Design

### Must contain

- End-to-end architecture interview
- Tradeoffs
- Scaling
- Failure modes
- Cost
- Security
- Observability
- RAG evaluation
- Agent reliability
- Deployment

### Final exercise

Design and explain a production AI system from scratch.

### Definition of Done

- Three portfolio projects are presentable.
- GitHub documentation is strong.
- Can explain architecture and tradeoffs.
- Can answer core AI Engineer interview questions.
- Can design an AI system from requirements to production.

---

# Global Definition of Done

At the end of 8 weeks, the learner should be able to:

- Integrate LLM APIs into applications.
- Build FastAPI AI backends.
- Generate structured LLM outputs.
- Stream model responses.
- Build RAG from first principles.
- Work with embeddings and vector databases.
- Implement chunking and retrieval.
- Implement hybrid search and reranking.
- Add citations.
- Evaluate RAG quality.
- Build tool-using agents.
- Implement agent loops and state.
- Design safe tool execution.
- Use retries, timeouts, and idempotency.
- Implement human approval.
- Understand MCP.
- Evaluate AI systems quantitatively.
- Understand core ML concepts.
- Build PyTorch training loops.
- Dockerize AI services.
- Build CI/CD.
- Deploy AI systems.
- Add logging, metrics, and tracing.
- Use queues/workers and caching.
- Apply authentication/authorization.
- Understand transformers and attention.
- Understand RAG vs fine-tuning.
- Understand LoRA/QLoRA conceptually.
- Identify and mitigate AI security risks.
- Design production AI architectures.
- Present three strong GitHub projects.
- Discuss AI system tradeoffs in technical interviews.

---

# Generation Contract

When asked:

> “Generate Day X of Week Y”

use this file as the curriculum specification.

The generated lesson must:

1. Stay within the assigned week's scope.
2. Cover every `Must contain` item for that day.
3. Connect to the previous day.
4. Include theory, code, exercise, mini-project, mini-test, interview questions, and Definition of Done.
5. Prefer implementation from first principles before introducing frameworks.
6. Make production considerations explicit.
7. Avoid teaching unrelated technologies merely because they are popular.
8. Keep the difficulty progressive.
9. Reuse the week's project so the six days produce a coherent deliverable.
10. End with a concrete skill check.

## Core Rule

For every technology learned, ask:

> **Can I build something with it that I can put on GitHub and discuss in a technical interview?**

If not, do not spend excessive time on it.

The objective is not to become an ML researcher in eight weeks.

The objective is to become a credible **AI Engineer who can build, integrate, evaluate, secure, and deploy AI systems.**
