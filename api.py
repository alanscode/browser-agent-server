import os
import json
import asyncio
import logging
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import uvicorn

# Load environment variables from .env file
load_dotenv()

# Import functionality from webui_core.py
from webui_core import (
    default_config,
    resolve_sensitive_env_variables,
    run_browser_agent,
    run_org_agent,
    run_custom_agent,
    run_deep_search,
    list_recordings,
    close_global_browser,
    _global_agent_state,
    _global_agent
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom JSON encoder to handle complex objects
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)

# Create FastAPI app
app = FastAPI(
    title="Browser Use API",
    description="REST API for Browser Use functionality",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Define Pydantic models for request/response
class ConfigModel(BaseModel):
    agent_type: str = "custom"
    max_steps: int = 100
    max_actions_per_step: int = 10
    use_vision: bool = True
    tool_calling_method: str = "auto"
    llm_provider: str = "anthropic"
    llm_model_name: str = "claude-3-5-sonnet-20241022"
    llm_num_ctx: int = 32000
    llm_temperature: float = 1.0
    llm_base_url: str = ""
    llm_api_key: str = ""
    use_own_browser: bool = False
    keep_browser_open: bool = False
    headless: bool = False
    disable_security: bool = True
    enable_recording: bool = True
    window_w: int = 1280
    window_h: int = 1100
    save_recording_path: str = "./tmp/record_videos"
    save_trace_path: str = "./tmp/traces"
    save_agent_history_path: str = "./tmp/agent_history"
    task: str = ""
    add_infos: Optional[str] = None

class AgentRunRequest(BaseModel):
    config: ConfigModel
    task: str
    add_infos: Optional[str] = None

class AgentRunResponse(BaseModel):
    final_result: str
    errors: str
    model_actions: str
    model_thoughts: str
    latest_video: Optional[str] = None
    trace_file: Optional[str] = None
    history_file: Optional[str] = None
    status: str = "completed"
    agent_id: Optional[str] = None

class DeepSearchRequest(BaseModel):
    research_task: str
    max_search_iterations: int = 3
    max_query_per_iteration: int = 1
    config: ConfigModel

class DeepSearchResponse(BaseModel):
    markdown_content: str
    file_path: Optional[str] = None
    status: str = "completed"

class RecordingInfo(BaseModel):
    path: str
    name: str

class StatusResponse(BaseModel):
    status: str
    message: str

# Background task to run the agent
async def run_agent_task(
    task_id: str,
    config: ConfigModel,
    task: str,
    add_infos: Optional[str] = None
) -> Dict[str, Any]:
    try:
        result = await run_browser_agent(
            agent_type=config.agent_type,
            llm_provider=config.llm_provider,
            llm_model_name=config.llm_model_name,
            llm_num_ctx=config.llm_num_ctx,
            llm_temperature=config.llm_temperature,
            llm_base_url=config.llm_base_url,
            llm_api_key=config.llm_api_key,
            use_own_browser=config.use_own_browser,
            keep_browser_open=config.keep_browser_open,
            headless=config.headless,
            disable_security=config.disable_security,
            window_w=config.window_w,
            window_h=config.window_h,
            save_recording_path=config.save_recording_path,
            save_agent_history_path=config.save_agent_history_path,
            save_trace_path=config.save_trace_path,
            enable_recording=config.enable_recording,
            task=task,
            add_infos=add_infos or "",
            max_steps=config.max_steps,
            use_vision=config.use_vision,
            max_actions_per_step=config.max_actions_per_step,
            tool_calling_method=config.tool_calling_method,
            chrome_cdp=""
        )
        
        # Correctly unpack all 10 values returned by run_browser_agent
        final_result, errors, model_actions, model_thoughts, latest_video, trace_file, history_file, _, _, _ = result
        
        return {
            "task_id": task_id,
            "final_result": final_result,
            "errors": errors,
            "model_actions": model_actions,
            "model_thoughts": model_thoughts,
            "latest_video": latest_video,
            "trace_file": trace_file,
            "history_file": history_file,
            "status": "completed"
        }
    except Exception as e:
        logger.error(f"Error running agent: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "task_id": task_id,
            "final_result": "",
            "errors": f"Error: {str(e)}",
            "model_actions": "",
            "model_thoughts": "",
            "latest_video": None,
            "trace_file": None,
            "history_file": None,
            "status": "error"
        }

# Store for running tasks
running_tasks = {}

# API endpoints
@app.get("/", response_model=StatusResponse)
async def root():
    return {"status": "ok", "message": "Browser Use API is running"}

@app.get("/config/default", response_model=ConfigModel)
async def get_default_config():
    """Get the default configuration"""
    config_dict = default_config()
    return config_dict

@app.post("/agent/run", response_model=StatusResponse)
async def start_agent_run(
    background_tasks: BackgroundTasks,
    request: AgentRunRequest
):
    """Start an agent run in the background"""
    task_id = f"task_{len(running_tasks) + 1}"
    
    # Start the agent run in the background
    background_tasks.add_task(
        run_agent_background,
        task_id,
        request.config,
        request.task,
        request.add_infos
    )
    
    running_tasks[task_id] = {"status": "running"}
    
    return {"status": "started", "message": f"Agent run started with ID: {task_id}"}

async def run_agent_background(task_id, config, task, add_infos):
    """Run the agent in the background and store the result"""
    try:
        logger.info(f"Starting agent run for task_id: {task_id}")
        result = await run_agent_task(task_id, config, task, add_infos)
        logger.info(f"Agent run completed for task_id: {task_id}")
        running_tasks[task_id] = result
    except Exception as e:
        logger.error(f"Unhandled exception in run_agent_background for task_id {task_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        running_tasks[task_id] = {
            "task_id": task_id,
            "final_result": "",
            "errors": f"Unhandled error: {str(e)}",
            "model_actions": "",
            "model_thoughts": "",
            "latest_video": None,
            "trace_file": None,
            "history_file": None,
            "status": "error"
        }

@app.get("/agent/status/{task_id}", response_model=Union[StatusResponse, AgentRunResponse])
async def get_agent_status(task_id: str):
    """Get the status of a running agent task"""
    if task_id not in running_tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    try:
        task_data = running_tasks[task_id]
        
        # If the task is just marked as running but has no other data yet
        if isinstance(task_data, dict) and len(task_data) == 1 and "status" in task_data and task_data["status"] == "running":
            return {"status": "running", "message": f"Task {task_id} is still initializing"}
        
        # Convert model_actions and model_thoughts to strings if they are lists
        if "model_actions" in task_data and not isinstance(task_data["model_actions"], str):
            task_data["model_actions"] = json.dumps(task_data["model_actions"], cls=CustomJSONEncoder)
        
        if "model_thoughts" in task_data and not isinstance(task_data["model_thoughts"], str):
            task_data["model_thoughts"] = json.dumps(task_data["model_thoughts"], cls=CustomJSONEncoder)
        
        # Ensure errors is a string
        if "errors" in task_data and not isinstance(task_data["errors"], str):
            task_data["errors"] = json.dumps(task_data["errors"], cls=CustomJSONEncoder) if task_data["errors"] else ""
        
        return task_data
    except Exception as e:
        logger.error(f"Error retrieving status for task {task_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error retrieving task status: {str(e)}")

@app.post("/agent/stop", response_model=StatusResponse)
async def stop_agent_run():
    """Stop the currently running agent"""
    try:
        if _global_agent:
            _global_agent.stop()
            return {"status": "success", "message": "Agent stop requested"}
        else:
            return {"status": "warning", "message": "No agent is currently running"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping agent: {str(e)}")

@app.post("/deep-search/run", response_model=StatusResponse)
async def start_deep_search(
    background_tasks: BackgroundTasks,
    request: DeepSearchRequest
):
    """Start a deep search in the background"""
    task_id = f"search_{len(running_tasks) + 1}"
    
    # Start the deep search in the background
    background_tasks.add_task(
        run_deep_search_background,
        task_id,
        request.research_task,
        request.max_search_iterations,
        request.max_query_per_iteration,
        request.config
    )
    
    running_tasks[task_id] = {"status": "running"}
    
    return {"status": "started", "message": f"Deep search started with ID: {task_id}"}

async def run_deep_search_background(task_id, research_task, max_search_iterations, max_query_per_iteration, config):
    """Run the deep search in the background and store the result"""
    try:
        logger.info(f"Starting deep search for task_id: {task_id}")
        result = await run_deep_search(
            research_task=research_task,
            max_search_iteration_input=max_search_iterations,
            max_query_per_iter_input=max_query_per_iteration,
            llm_provider=config.llm_provider,
            llm_model_name=config.llm_model_name,
            llm_num_ctx=config.llm_num_ctx,
            llm_temperature=config.llm_temperature,
            llm_base_url=config.llm_base_url,
            llm_api_key=config.llm_api_key,
            use_vision=config.use_vision,
            use_own_browser=config.use_own_browser,
            headless=config.headless,
            chrome_cdp=""
        )
        
        # Correctly unpack all 5 values returned by run_deep_search
        markdown_content, file_path, _, _, _ = result
        
        logger.info(f"Deep search completed for task_id: {task_id}")
        running_tasks[task_id] = {
            "task_id": task_id,
            "markdown_content": markdown_content,
            "file_path": file_path,
            "status": "completed"
        }
    except Exception as e:
        logger.error(f"Unhandled exception in run_deep_search_background for task_id {task_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        running_tasks[task_id] = {
            "task_id": task_id,
            "markdown_content": f"Error: {str(e)}",
            "file_path": None,
            "status": "error"
        }

@app.get("/deep-search/status/{task_id}", response_model=Union[StatusResponse, DeepSearchResponse])
async def get_deep_search_status(task_id: str):
    """Get the status of a running deep search task"""
    if task_id not in running_tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    try:
        task_data = running_tasks[task_id]
        
        # If the task is just marked as running but has no other data yet
        if isinstance(task_data, dict) and len(task_data) == 1 and "status" in task_data and task_data["status"] == "running":
            return {"status": "running", "message": f"Task {task_id} is still initializing"}
        
        return task_data
    except Exception as e:
        logger.error(f"Error retrieving status for deep search task {task_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error retrieving task status: {str(e)}")

@app.post("/deep-search/stop", response_model=StatusResponse)
async def stop_deep_search():
    """Stop the currently running deep search"""
    try:
        _global_agent_state.request_stop()
        return {"status": "success", "message": "Deep search stop requested"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping deep search: {str(e)}")

@app.get("/recordings", response_model=List[RecordingInfo])
async def get_recordings(path: str = "./tmp/record_videos"):
    """Get a list of available recordings"""
    try:
        recordings = list_recordings(path)
        return [{"path": rec[0], "name": rec[1]} for rec in recordings]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing recordings: {str(e)}")

@app.get("/recordings/{filename}")
async def get_recording(filename: str, path: str = "./tmp/record_videos"):
    """Get a specific recording file"""
    full_path = os.path.join(path, filename)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail=f"Recording {filename} not found")
    
    return FileResponse(full_path)

@app.post("/browser/close", response_model=StatusResponse)
async def close_browser():
    """Close the browser instance"""
    try:
        await close_global_browser()
        return {"status": "success", "message": "Browser closed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error closing browser: {str(e)}")

@app.get("/agent/history/{filename}")
async def get_agent_history(filename: str, path: str = "./tmp/agent_history"):
    """Get a specific agent history file"""
    # Ensure the filename doesn't contain path traversal
    safe_filename = os.path.basename(filename)
    full_path = os.path.join(path, safe_filename)
    
    logger.info(f"Requested history file: {safe_filename}, full path: {full_path}")
    
    if not os.path.exists(full_path):
        logger.error(f"History file not found: {full_path}")
        # List available files for debugging
        available_files = os.listdir(path) if os.path.exists(path) else []
        logger.info(f"Available files in {path}: {available_files}")
        raise HTTPException(status_code=404, detail=f"History file {safe_filename} not found. Available files: {available_files}")
    
    try:
        logger.info(f"Reading history file: {full_path}")
        with open(full_path, 'r') as f:
            history_data = json.load(f)
        logger.info(f"Successfully read history file: {full_path}")
        return history_data
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON from history file {full_path}: {str(e)}")
        # Return file content for debugging
        try:
            with open(full_path, 'r') as f:
                content = f.read()
            return {"error": f"Invalid JSON in history file: {str(e)}", "file_content": content[:1000] + "..." if len(content) > 1000 else content}
        except Exception as read_error:
            raise HTTPException(status_code=500, detail=f"Error reading history file: {str(read_error)}")
    except Exception as e:
        logger.error(f"Error reading history file {full_path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error reading history file: {str(e)}")

@app.get("/agent/history-files")
async def list_agent_history_files(path: str = "./tmp/agent_history"):
    """List all available agent history files"""
    try:
        if not os.path.exists(path):
            return {"files": []}
        
        files = [f for f in os.listdir(path) if f.endswith('.json')]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(path, x)), reverse=True)
        
        return {"files": files}
    except Exception as e:
        logger.error(f"Error listing history files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing history files: {str(e)}")

# Run the API server
if __name__ == "__main__":
    import argparse
    
    # Get default port from environment variable
    default_port = int(os.getenv("API_BASE_PORT", "8000"))
    
    parser = argparse.ArgumentParser(description="Browser Use API Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=default_port, help=f"Port to listen on (default: {default_port})")
    args = parser.parse_args()
    
    uvicorn.run("api:app", host=args.host, port=args.port, reload=True) 