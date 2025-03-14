#!/usr/bin/env python3
"""
Simple client for the Browser Use API.
This script demonstrates how to interact with the API endpoints.
"""

import requests
import json
import time
import argparse
import sys

class BrowserUseClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        
    def check_api_status(self):
        """Check if the API is running"""
        response = requests.get(f"{self.base_url}/")
        return response.json()
        
    def get_default_config(self):
        """Get the default configuration"""
        response = requests.get(f"{self.base_url}/config/default")
        return response.json()
    
    def run_agent(self, task, add_infos=None, custom_config=None):
        """Start an agent run with the given task"""
        # Get default config if no custom config is provided
        if custom_config is None:
            config = self.get_default_config()
        else:
            config = custom_config
            
        # Prepare the request payload
        payload = {
            "config": config,
            "task": task
        }
        
        if add_infos:
            payload["add_infos"] = add_infos
            
        # Start the agent run
        response = requests.post(f"{self.base_url}/agent/run", json=payload)
        result = response.json()
        
        if response.status_code != 200:
            print(f"Error starting agent: {result}")
            return None
            
        # Extract the task ID
        task_id = result["message"].split("ID: ")[1]
        print(f"Agent run started with ID: {task_id}")
        
        # Poll for the result
        return self.poll_agent_status(task_id)
    
    def poll_agent_status(self, task_id, interval=2, timeout=300):
        """Poll for the status of an agent run until it completes or times out"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = requests.get(f"{self.base_url}/agent/status/{task_id}")
            
            if response.status_code != 200:
                print(f"Error checking status: {response.json()}")
                return None
                
            result = response.json()
            
            if result.get("status") == "completed" or result.get("status") == "error":
                return result
                
            print(f"Task {task_id} is still running... (elapsed: {int(time.time() - start_time)}s)")
            time.sleep(interval)
            
        print(f"Timeout reached after {timeout} seconds")
        return None
    
    def stop_agent(self):
        """Stop the currently running agent"""
        response = requests.post(f"{self.base_url}/agent/stop")
        return response.json()
    
    def run_deep_search(self, research_task, max_iterations=3, max_queries=1, custom_config=None):
        """Start a deep search with the given research task"""
        # Get default config if no custom config is provided
        if custom_config is None:
            config = self.get_default_config()
        else:
            config = custom_config
            
        # Prepare the request payload
        payload = {
            "research_task": research_task,
            "max_search_iterations": max_iterations,
            "max_query_per_iteration": max_queries,
            "config": config
        }
            
        # Start the deep search
        response = requests.post(f"{self.base_url}/deep-search/run", json=payload)
        result = response.json()
        
        if response.status_code != 200:
            print(f"Error starting deep search: {result}")
            return None
            
        # Extract the task ID
        task_id = result["message"].split("ID: ")[1]
        print(f"Deep search started with ID: {task_id}")
        
        # Poll for the result
        return self.poll_deep_search_status(task_id)
    
    def poll_deep_search_status(self, task_id, interval=2, timeout=600):
        """Poll for the status of a deep search until it completes or times out"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = requests.get(f"{self.base_url}/deep-search/status/{task_id}")
            
            if response.status_code != 200:
                print(f"Error checking status: {response.json()}")
                return None
                
            result = response.json()
            
            if result.get("status") == "completed" or result.get("status") == "error":
                return result
                
            print(f"Task {task_id} is still running... (elapsed: {int(time.time() - start_time)}s)")
            time.sleep(interval)
            
        print(f"Timeout reached after {timeout} seconds")
        return None
    
    def stop_deep_search(self):
        """Stop the currently running deep search"""
        response = requests.post(f"{self.base_url}/deep-search/stop")
        return response.json()
    
    def get_recordings(self, path=None):
        """Get a list of available recordings"""
        url = f"{self.base_url}/recordings"
        if path:
            url += f"?path={path}"
            
        response = requests.get(url)
        return response.json()
    
    def close_browser(self):
        """Close the browser instance"""
        response = requests.post(f"{self.base_url}/browser/close")
        return response.json()

def main():
    parser = argparse.ArgumentParser(description="Browser Use API Client")
    parser.add_argument("--url", type=str, default="http://localhost:8000", help="API base URL")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Status command
    subparsers.add_parser("status", help="Check API status")
    
    # Config command
    subparsers.add_parser("config", help="Get default configuration")
    
    # Run agent command
    run_parser = subparsers.add_parser("run", help="Run an agent task")
    run_parser.add_argument("task", type=str, help="Task description")
    run_parser.add_argument("--info", type=str, help="Additional information for the task")
    
    # Stop agent command
    subparsers.add_parser("stop", help="Stop the currently running agent")
    
    # Run deep search command
    search_parser = subparsers.add_parser("search", help="Run a deep search")
    search_parser.add_argument("task", type=str, help="Research task description")
    search_parser.add_argument("--iterations", type=int, default=3, help="Maximum search iterations")
    search_parser.add_argument("--queries", type=int, default=1, help="Maximum queries per iteration")
    
    # Stop deep search command
    subparsers.add_parser("stop-search", help="Stop the currently running deep search")
    
    # List recordings command
    recordings_parser = subparsers.add_parser("recordings", help="List available recordings")
    recordings_parser.add_argument("--path", type=str, help="Path to look for recordings")
    
    # Close browser command
    subparsers.add_parser("close-browser", help="Close the browser instance")
    
    args = parser.parse_args()
    
    # Create client
    client = BrowserUseClient(args.url)
    
    # Execute command
    if args.command == "status":
        result = client.check_api_status()
        print(json.dumps(result, indent=2))
        
    elif args.command == "config":
        result = client.get_default_config()
        print(json.dumps(result, indent=2))
        
    elif args.command == "run":
        result = client.run_agent(args.task, args.info)
        if result:
            print("\nAgent run completed:")
            print(f"Final result: {result.get('final_result', '')}")
            print(f"Errors: {result.get('errors', '')}")
            
    elif args.command == "stop":
        result = client.stop_agent()
        print(json.dumps(result, indent=2))
        
    elif args.command == "search":
        result = client.run_deep_search(args.task, args.iterations, args.queries)
        if result:
            print("\nDeep search completed:")
            print(f"Markdown content: {result.get('markdown_content', '')[:500]}...")
            print(f"File path: {result.get('file_path', '')}")
            
    elif args.command == "stop-search":
        result = client.stop_deep_search()
        print(json.dumps(result, indent=2))
        
    elif args.command == "recordings":
        result = client.get_recordings(args.path)
        print(json.dumps(result, indent=2))
        
    elif args.command == "close-browser":
        result = client.close_browser()
        print(json.dumps(result, indent=2))
        
    else:
        parser.print_help()
        
if __name__ == "__main__":
    main() 