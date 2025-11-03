# mindiv

AI agent backend specialized in solving complex mathematical and physics reasoning tasks.

## Features

- **DeepThink Engine**: Single-agent iterative reasoning with verification loops
- **UltraThink Engine**: Multi-agent parallel exploration with synthesis
- **Multi-Provider Support**: OpenAI, Anthropic Claude, Google Gemini
- **Prefix Caching**: Provider-side (OpenAI Responses API) and local disk caching
- **Token Tracking**: Comprehensive usage and cost estimation
- **Stage-Based Routing**: Different models for different reasoning stages

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or with specific Python version
/Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10 -m pip install --user -r requirements.txt
```

### Configuration

```bash
# Copy example configuration
cp config/config.yaml.example config/config.yaml

# Edit config.yaml and add your API keys
# - OPENAI_API_KEY
# - ANTHROPIC_API_KEY
# - GEMINI_API_KEY
```

### Running the Service

```bash
# Using the run script
python run.py

# Or directly with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Testing

```bash
# Run basic functionality tests
python test_basic.py
```

## API Endpoints

### OpenAI-Compatible Endpoints

#### Chat Completions
```bash
POST /v1/chat/completions
```

Example:
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-deepthink",
    "messages": [
      {"role": "user", "content": "Solve x^2 + 5x + 6 = 0"}
    ]
  }'
```

#### Responses API (with caching)
```bash
POST /v1/responses
```

Example:
```bash
curl -X POST http://localhost:8000/v1/responses \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-deepthink",
    "input": "Prove that sqrt(2) is irrational",
    "store": true
  }'
```

#### List Models
```bash
GET /v1/models
```

### Engine Endpoints

#### DeepThink
```bash
POST /mindiv/deepthink
```

Example:
```bash
curl -X POST http://localhost:8000/mindiv/deepthink \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-deepthink",
    "problem": "Prove that sqrt(2) is irrational",
    "max_iterations": 30,
    "required_verifications": 3
  }'
```

Response:
```json
{
  "solution": "...",
  "iterations": 15,
  "verifications": 3,
  "token_usage": {
    "total_usage": {
      "input_tokens": 5000,
      "output_tokens": 2000,
      "cached_tokens": 1000,
      "reasoning_tokens": 500
    },
    "estimated_cost": 0.15
  }
}
```

#### UltraThink
```bash
POST /mindiv/ultrathink
```

Example:
```bash
curl -X POST http://localhost:8000/mindiv/ultrathink \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-ultrathink",
    "problem": "Find all integer solutions to x^3 + y^3 = z^3",
    "num_agents": 5,
    "max_iterations_per_agent": 10
  }'
```

Response:
```json
{
  "summary": "...",
  "plan": "...",
  "agent_results": [...],
  "synthesis": "...",
  "token_usage": {
    "total_usage": {
      "input_tokens": 15000,
      "output_tokens": 8000,
      "cached_tokens": 3000,
      "reasoning_tokens": 2000
    },
    "estimated_cost": 0.45
  }
}
```

## Configuration

### Provider Configuration

```yaml
providers:
  openai:
    base_url: "https://api.openai.com/v1"
    api_key: "${OPENAI_API_KEY}"
    supports_responses: true
    supports_streaming: true
    timeout: 300
    max_retries: 3
```

### Model Configuration

```yaml
models:
  gpt-4o-deepthink:
    name: "GPT-4O DeepThink"
    provider: openai
    model: gpt-4o
    level: deepthink
    max_iterations: 30
    required_verifications: 3
    stage_models:
      initial: gpt-4o
      improvement: gpt-4o
      verification: gpt-4o-mini
      correction: gpt-4o
      summary: gpt-4o
```

## Architecture

### DeepThink Workflow

1. **Initial Exploration**: Generate initial solution with system prompt
2. **Verification**: Verify solution using LLM or arithmetic checks
3. **Correction**: If verification fails, generate improved solution
4. **Iteration**: Repeat until required verifications pass
5. **Summary**: Generate final summary

### UltraThink Workflow

1. **Planning**: Generate high-level plan for solving the problem
2. **Agent Configuration**: Create N agent configurations with diverse approaches
3. **Parallel Execution**: Run N DeepThink agents in parallel
4. **Synthesis**: Synthesize results into unified solution
5. **Summary**: Generate user-facing summary

### Provider Abstraction

All providers implement a common interface:
- `chat()`: Standard chat completion
- `chat_stream()`: Streaming chat completion
- `response()`: Responses API with caching (OpenAI only)
- `capabilities`: Feature flags (responses, streaming, vision, thinking, caching)

### Token Tracking

- Input tokens
- Output tokens
- Cached tokens (OpenAI)
- Reasoning tokens (OpenAI o1/responses)
- Cost estimation based on pricing.yaml

## Project Structure

```
mindiv/
├── config/          # Configuration management
├── providers/       # LLM provider adapters
├── utils/           # Utilities (caching, token tracking, messages)
├── engine/          # Reasoning engines (DeepThink, UltraThink)
├── api/v1/          # API routes
├── main.py          # FastAPI application
├── run.py           # Runner script
└── test_basic.py    # Basic tests
```

## Development

### Running Tests

```bash
python test_basic.py
```

### Adding a New Provider

1. Create provider adapter in `providers/`
2. Implement `LLMProvider` protocol
3. Register in `providers/registry.py`
4. Add configuration in `config.yaml`
5. Add pricing in `pricing.yaml`

## License

See parent project for license information.

