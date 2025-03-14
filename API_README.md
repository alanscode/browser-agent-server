# Browser Use REST API

This document describes the REST API for Browser Use, which allows you to programmatically control browser automation tasks using AI agents.

## Getting Started

### Starting the API Server

```bash
# Start the API server on the default port (8000)
python api.py

# Start the API server on a custom host and port
python api.py --host 0.0.0.0 --port 9000
```

### Using the API Client

A Python client is provided for easy interaction with the API:

```bash
# Check API status
python api_client.py status

# Get default configuration
python api_client.py config

# Run an agent task
python api_client.py run "go to google.com and search for 'OpenAI'"

# Run a deep search task
python api_client.py search "Research the latest advancements in AI"

# List available recordings
python api_client.py recordings

# Stop the currently running agent
python api_client.py stop

# Close the browser instance
python api_client.py close-browser
```

## API Endpoints

### General

#### `GET /`

Check if the API is running.

**Response:**
```json
{
  "status": "ok",
  "message": "Browser Use API is running"
}
```

### Configuration

#### `GET /config/default`

Get the default configuration.

**Response:**
```json
{
  "agent_type": "custom",
  "max_steps": 100,
  "max_actions_per_step": 10,
  "use_vision": true,
  "tool_calling_method": "auto",
  "llm_provider": "anthropic",
  "llm_model_name": "claude-3-5-sonnet-20241022",
  "llm_num_ctx": 32000,
  "llm_temperature": 1.0,
  "llm_base_url": "",
  "llm_api_key": "",
  "use_own_browser": false,
  "keep_browser_open": false,
  "headless": false,
  "disable_security": true,
  "enable_recording": true,
  "window_w": 1280,
  "window_h": 1100,
  "save_recording_path": "./tmp/record_videos",
  "save_trace_path": "./tmp/traces",
  "save_agent_history_path": "./tmp/agent_history",
  "task": ""
}
```

### Agent Operations

#### `POST /agent/run`

Start an agent run in the background.

**Request:**
```json
{
  "config": {
    "agent_type": "custom",
    "max_steps": 100,
    "max_actions_per_step": 10,
    "use_vision": true,
    "tool_calling_method": "auto",
    "llm_provider": "anthropic",
    "llm_model_name": "claude-3-5-sonnet-20241022",
    "llm_num_ctx": 32000,
    "llm_temperature": 1.0,
    "llm_base_url": "",
    "llm_api_key": "",
    "use_own_browser": false,
    "keep_browser_open": false,
    "headless": true,
    "disable_security": true,
    "enable_recording": true,
    "window_w": 1280,
    "window_h": 1100,
    "save_recording_path": "./tmp/record_videos",
    "save_trace_path": "./tmp/traces",
    "save_agent_history_path": "./tmp/agent_history"
  },
  "task": "go to google.com and search for 'OpenAI'",
  "add_infos": "Optional additional information"
}
```

**Response:**
```json
{
  "status": "started",
  "message": "Agent run started with ID: task_1"
}
```

#### `GET /agent/status/{task_id}`

Get the status of a running agent task.

**Response (running):**
```json
{
  "status": "running"
}
```

**Response (completed):**
```json
{
  "task_id": "task_1",
  "final_result": "The first URL for OpenAI is https://openai.com/",
  "errors": "",
  "model_actions": "...",
  "model_thoughts": "...",
  "latest_video": "/path/to/recording.mp4",
  "trace_file": "/path/to/trace.zip",
  "history_file": "/path/to/history.json",
  "status": "completed"
}
```

#### `POST /agent/stop`

Stop the currently running agent.

**Response:**
```json
{
  "status": "success",
  "message": "Agent stop requested"
}
```

### Deep Search Operations

#### `POST /deep-search/run`

Start a deep search in the background.

**Request:**
```json
{
  "research_task": "Research the latest advancements in AI",
  "max_search_iterations": 3,
  "max_query_per_iteration": 1,
  "config": {
    "llm_provider": "anthropic",
    "llm_model_name": "claude-3-5-sonnet-20241022",
    "llm_num_ctx": 32000,
    "llm_temperature": 1.0,
    "llm_base_url": "",
    "llm_api_key": "",
    "use_vision": true,
    "use_own_browser": false,
    "headless": true
  }
}
```

**Response:**
```json
{
  "status": "started",
  "message": "Deep search started with ID: search_1"
}
```

#### `GET /deep-search/status/{task_id}`

Get the status of a running deep search task.

**Response (running):**
```json
{
  "status": "running"
}
```

**Response (completed):**
```json
{
  "task_id": "search_1",
  "markdown_content": "# Research on Latest AI Advancements\n\n...",
  "file_path": "/path/to/research.md",
  "status": "completed"
}
```

#### `POST /deep-search/stop`

Stop the currently running deep search.

**Response:**
```json
{
  "status": "success",
  "message": "Deep search stop requested"
}
```

### Recordings

#### `GET /recordings`

Get a list of available recordings.

**Query Parameters:**
- `path` (optional): Path to look for recordings (default: "./tmp/record_videos")

**Response:**
```json
[
  {
    "path": "/path/to/recording1.mp4",
    "name": "1. recording1.mp4"
  },
  {
    "path": "/path/to/recording2.mp4",
    "name": "2. recording2.mp4"
  }
]
```

#### `GET /recordings/{filename}`

Get a specific recording file.

**Response:**
The video file as a binary stream.

### Browser Management

#### `POST /browser/close`

Close the browser instance.

**Response:**
```json
{
  "status": "success",
  "message": "Browser closed successfully"
}
```

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

Error responses include a JSON object with details:

```json
{
  "detail": "Error message"
}
```

## Authentication

This API does not include authentication. If deploying in a production environment, it is recommended to add authentication middleware or run the API behind a secure proxy.

## Examples

### Running an Agent Task with cURL

```bash
curl -X POST http://localhost:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "agent_type": "custom",
      "max_steps": 100,
      "headless": true,
      "llm_provider": "anthropic",
      "llm_model_name": "claude-3-5-sonnet-20241022"
    },
    "task": "go to google.com and search for OpenAI"
  }'
```

### Checking Task Status with cURL

```bash
curl -X GET http://localhost:8000/agent/status/task_1
```

### Running a Deep Search with cURL

```bash
curl -X POST http://localhost:8000/deep-search/run \
  -H "Content-Type: application/json" \
  -d '{
    "research_task": "Research the latest advancements in AI",
    "max_search_iterations": 3,
    "max_query_per_iteration": 1,
    "config": {
      "llm_provider": "anthropic",
      "llm_model_name": "claude-3-5-sonnet-20241022",
      "headless": true
    }
  }'
``` 