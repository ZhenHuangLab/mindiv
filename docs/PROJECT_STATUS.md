# mindiv Project Status

## Overview

`mindiv` is a Python-based AI agent backend specialized in solving complex mathematical and physics reasoning tasks. It implements and enhances DeepThink/UltraThink reasoning engines with multi-provider support, prefix caching, and comprehensive token tracking.

## Completed Components

### 1. Configuration System (`mindiv/config/`)

- ✅ `config.py` - Configuration dataclasses and YAML loading
  - `ProviderConfig` - Provider settings (API keys, URLs, capabilities)
  - `ModelConfig` - Model settings (iterations, verifications, stage routing)
  - `Config` - Global configuration with pricing data
  - `load_config()` - YAML configuration loader
  - `get_config()` / `set_config()` - Global config management

- ✅ `config.yaml.example` - Configuration template with examples
  - System settings (host, port, API key, logging)
  - Provider configurations (OpenAI, Anthropic, Gemini)
  - Model configurations (DeepThink, UltraThink examples)
  - Stage-specific model routing

- ✅ `pricing.yaml` - Token pricing data
  - OpenAI models (gpt-4o, gpt-4o-mini, o1, o1-mini)
  - Anthropic models (claude-sonnet-4, claude-opus-4)
  - Gemini models (gemini-2.5-pro, gemini-2.5-flash, gemini-2.0-flash-thinking)
  - Includes prompt, completion, reasoning, and cached_prompt rates

### 2. Provider Infrastructure (`mindiv/providers/`)

- ✅ `base.py` - Provider protocol and capabilities
  - `LLMProvider` - Protocol defining provider interface
  - `ProviderCapabilities` - Feature flags (responses, streaming, vision, thinking, caching)

- ✅ `registry.py` - Provider registry and factory
  - `ProviderRegistry` - Class-based registry for provider adapters
  - `create_provider()` - Factory function for provider instantiation
  - `register_builtin_providers()` - Registers OpenAI, Anthropic, Gemini
  - `resolve_model_and_provider()` - Resolves model ID to provider instance

- ✅ `openai.py` - OpenAI provider adapter
  - Chat completions API support
  - Responses API support with prefix caching
  - Streaming support
  - Token usage tracking with cached/reasoning tokens

- ✅ `anthropic.py` - Anthropic Claude provider adapter
  - Messages API support
  - Streaming support
  - Prompt caching support

- ✅ `gemini.py` - Google Gemini provider adapter
  - systemInstruction support
  - thinkingConfig support for thinking models
  - Streaming support

### 3. Utility Modules (`mindiv/utils/`)

- ✅ `token_meter.py` - Token usage tracking and cost estimation
  - `UsageStats` - Token usage statistics dataclass
  - `TokenMeter` - Tracks usage across providers/models
  - Cost estimation based on pricing data
  - Detailed usage summaries by provider and model

- ✅ `cache.py` - Prefix caching manager
  - `PrefixCache` - Manages both provider-side and local disk caching
  - OpenAI responses API integration (previous_response_id)
  - Local disk cache using diskcache
  - Cache key computation from prompt components

- ✅ `messages.py` - Message utilities
  - `normalize_messages()` - Message format normalization
  - `extract_text_content()` - Multi-modal content extraction
  - `build_message()` - Message construction helpers
  - `merge_system_prompts()` - System prompt merging
  - `format_conversation_history()` - History management
  - `ensure_messages()` / `extract_text()` - Compatibility helpers

### 4. Engine Modules (`mindiv/engine/`)

- ✅ `prompts.py` - Prompt templates
  - DeepThink prompts (initial, verification, correction)
  - UltraThink prompts (planning, agent generation, synthesis)
  - Math-specific verification prompts

- ✅ `verify.py` - Verification utilities
  - `verify_with_llm()` - LLM-based solution verification
  - `arithmetic_sanity_check()` - SymPy-based arithmetic validation

- ✅ `deep_think.py` - DeepThink engine
  - Single-agent iterative reasoning
  - Verification loops with correction
  - Stage-aware model routing
  - Prefix caching support
  - Token usage tracking
  - Progress callbacks

- ✅ `ultra_think.py` - UltraThink engine
  - Multi-agent parallel exploration
  - Plan generation
  - Agent configuration generation
  - Parallel DeepThink execution
  - Result synthesis
  - Token usage tracking across all agents

- ✅ `planning.py` - Planning utilities
  - `generate_plan()` - High-level plan generation for UltraThink

### 5. API Routes (`mindiv/api/v1/`)

- ✅ `chat.py` - OpenAI-compatible chat completions endpoint
  - `/v1/chat/completions` - Standard chat API
  - Model resolution and provider routing
  - Error handling

- ✅ `responses.py` - OpenAI-compatible responses endpoint
  - `/v1/responses` - Responses API with caching
  - Input normalization (string or messages)
  - Provider capability checking

- ✅ `models.py` - Models listing endpoint
  - `/v1/models` - List available models
  - Model metadata and features

- ✅ `engines.py` - Engine-specific endpoints
  - `/mindiv/deepthink` - DeepThink engine endpoint
  - `/mindiv/ultrathink` - UltraThink engine endpoint
  - Token usage and cost reporting

### 6. Main Application (`mindiv/`)

- ✅ `main.py` - FastAPI application
  - Application lifespan management
  - Configuration loading
  - Provider registration
  - CORS middleware
  - API key authentication
  - Health check endpoints

- ✅ `run.py` - Simple runner script
  - Configuration loading
  - Uvicorn server startup

- ✅ `requirements.txt` - Python dependencies
  - FastAPI, Uvicorn, Pydantic
  - OpenAI, Anthropic, httpx
  - diskcache, sympy
  - pytest for testing

- ✅ `test_basic.py` - Basic functionality tests
  - Import tests
  - Configuration tests
  - Provider registration tests
  - Token meter tests

## Architecture Highlights

### DeepThink Workflow
1. Initial exploration with system prompt
2. LLM-based verification
3. Iterative correction based on feedback
4. Multiple verification passes required
5. Final summary generation

### UltraThink Workflow
1. Generate high-level plan
2. Create N agent configurations with diverse approaches
3. Run N DeepThink agents in parallel
4. Synthesize results into unified solution
5. Generate user-facing summary

### Provider Abstraction
- Unified interface across OpenAI, Anthropic, Gemini
- Capability-based feature detection
- Automatic fallback for unsupported features
- Provider-side caching (OpenAI responses)
- Local disk caching (all providers)

### Token Tracking
- Per-provider, per-model usage tracking
- Cached token tracking (OpenAI)
- Reasoning token tracking (OpenAI o1/responses)
- Cost estimation based on pricing data
- Detailed usage summaries

### Stage-Based Routing
- Different models for different stages
- Initial exploration (powerful model)
- Verification (cheaper model)
- Correction (powerful model)
- Summary (medium model)

## Next Steps (Not Implemented)

The following features were planned but not implemented in this phase:

1. **Memory Folding** - Episodic/working memory for long horizons
2. **Parallel Verification** - Multiple verification workers
3. **Advanced Planning** - More sophisticated decomposition strategies
4. **Tool Integration** - External tool calls (calculators, provers)
5. **Streaming Support** - Server-sent events for real-time updates
6. **Rate Limiting** - Per-model RPM enforcement
7. **Persistent Storage** - Database for conversation history
8. **Authentication** - More sophisticated auth mechanisms
9. **Monitoring** - Metrics and observability
10. **Unit Tests** - Comprehensive test coverage

## Usage

### Starting the Service

```bash
# Install dependencies
pip install -r mindiv/requirements.txt

# Copy and configure
cp mindiv/config/config.yaml.example mindiv/config/config.yaml
# Edit config.yaml with your API keys

# Run the service
python mindiv/run.py
```

### API Examples

```bash
# Chat completion
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-deepthink",
    "messages": [{"role": "user", "content": "Solve x^2 + 5x + 6 = 0"}]
  }'

# DeepThink engine
curl -X POST http://localhost:8000/mindiv/deepthink \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-deepthink",
    "problem": "Prove that sqrt(2) is irrational"
  }'

# UltraThink engine
curl -X POST http://localhost:8000/mindiv/ultrathink \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-ultrathink",
    "problem": "Find all integer solutions to x^3 + y^3 = z^3",
    "num_agents": 5
  }'
```

## File Structure

```
mindiv/
├── __init__.py
├── main.py                 # FastAPI application
├── run.py                  # Runner script
├── test_basic.py          # Basic tests
├── requirements.txt       # Dependencies
├── PROJECT_STATUS.md      # This file
├── config/
│   ├── __init__.py
│   ├── config.py          # Configuration classes
│   ├── config.yaml.example # Config template
│   └── pricing.yaml       # Pricing data
├── providers/
│   ├── __init__.py
│   ├── base.py            # Provider protocol
│   ├── registry.py        # Provider registry
│   ├── openai.py          # OpenAI adapter
│   ├── anthropic.py       # Anthropic adapter
│   └── gemini.py          # Gemini adapter
├── utils/
│   ├── __init__.py
│   ├── token_meter.py     # Token tracking
│   ├── cache.py           # Prefix caching
│   └── messages.py        # Message utilities
├── engine/
│   ├── __init__.py
│   ├── prompts.py         # Prompt templates
│   ├── verify.py          # Verification
│   ├── planning.py        # Planning utilities
│   ├── deep_think.py      # DeepThink engine
│   └── ultra_think.py     # UltraThink engine
└── api/
    └── v1/
        ├── __init__.py
        ├── chat.py        # Chat endpoint
        ├── responses.py   # Responses endpoint
        ├── models.py      # Models endpoint
        └── engines.py     # Engine endpoints
```

## Status: ✅ COMPLETE

All planned components for the initial phase have been implemented and are ready for testing.

