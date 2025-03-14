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
import os
from dotenv import load_dotenv
import urllib.parse

# Load environment variables from .env file
load_dotenv()

class BrowserUseClient:
    def __init__(self, base_url=None):
        # Use the provided base_url, or construct it from environment variables
        if base_url:
            self.base_url = base_url
        else:
            # Get base URL and port from environment variables
            base_url = os.getenv("API_BASE_URL", "http://localhost")
            base_port = os.getenv("API_BASE_PORT", "8000")
            
            # Remove any trailing slashes from the base_url
            base_url = base_url.rstrip('/')
            
            # Check if the base_url already includes a port
            # Parse the URL to check for port
            parsed_url = urllib.parse.urlparse(base_url)
            
            if parsed_url.port:
                self.base_url = base_url
            else:
                self.base_url = f"{base_url}:{base_port}"
        
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
        
        if response.status_code != 200:
            print(f"Error starting agent: Status code {response.status_code}")
            try:
                result = response.json()
                print(f"Error details: {result}")
            except json.JSONDecodeError:
                print(f"Error details (raw): {response.text}")
            return None
            
        try:
            result = response.json()
            # Extract the task ID
            task_id = result["message"].split("ID: ")[1]
            print(f"Agent run started with ID: {task_id}")
            
            # Poll for the result
            return self.poll_agent_status(task_id)
        except (KeyError, json.JSONDecodeError) as e:
            print(f"Error parsing response: {e}")
            print(f"Raw response: {response.text}")
            return None
    
    def poll_agent_status(self, task_id, interval=2, timeout=300, max_retries=3):
        """Poll for the status of an agent run until it completes or times out"""
        start_time = time.time()
        retries = 0
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.base_url}/agent/status/{task_id}")
                
                if response.status_code != 200:
                    print(f"Error checking status: Status code {response.status_code}")
                    try:
                        error_details = response.json()
                        print(f"Error details: {error_details}")
                    except json.JSONDecodeError:
                        print(f"Error details (raw): {response.text}")
                    
                    # Retry a few times for server errors (5xx)
                    if 500 <= response.status_code < 600 and retries < max_retries:
                        retries += 1
                        print(f"Retrying in {interval} seconds... (retry {retries}/{max_retries})")
                        time.sleep(interval)
                        continue
                    
                    return None
                
                # Reset retry counter on successful response
                retries = 0
                
                # Try to parse the JSON response
                try:
                    result = response.json()
                except json.JSONDecodeError:
                    print(f"Error: Invalid JSON response from server")
                    print(f"Raw response: {response.text}")
                    # Wait and retry - this might be a temporary issue
                    time.sleep(interval)
                    continue
                
                if result.get("status") == "completed" or result.get("status") == "error":
                    return result
                    
                print(f"Task {task_id} is still running... (elapsed: {int(time.time() - start_time)}s)")
                time.sleep(interval)
            except requests.RequestException as e:
                print(f"Network error while checking status: {e}")
                
                # Retry a few times for network errors
                if retries < max_retries:
                    retries += 1
                    print(f"Retrying in {interval} seconds... (retry {retries}/{max_retries})")
                    time.sleep(interval)
                    continue
                else:
                    print(f"Maximum retries ({max_retries}) reached. Giving up.")
                    return None
                
        print(f"Timeout reached after {timeout} seconds")
        return None
    
    def stop_agent(self):
        """Stop the currently running agent"""
        response = requests.post(f"{self.base_url}/agent/stop")
        return response.json()
    
    def run_deep_search(self, research_task, max_iterations=3, max_queries=1, custom_config=None):
        """Start a deep search with the given research task"""
        print("Deep search functionality is currently disabled.")
        print("This feature has been temporarily disabled to focus on core agent functionality.")
        return {
            "status": "disabled",
            "message": "Deep search functionality is currently disabled."
        }
        
    def poll_deep_search_status(self, task_id, interval=2, timeout=600):
        """Poll for the status of a deep search until it completes or times out"""
        print("Deep search functionality is currently disabled.")
        return {
            "status": "disabled",
            "message": "Deep search functionality is currently disabled."
        }
    
    def stop_deep_search(self):
        """Stop the currently running deep search"""
        print("Deep search functionality is currently disabled.")
        return {
            "status": "disabled",
            "message": "Deep search functionality is currently disabled."
        }
    
    def get_recordings(self, path=None):
        """Get a list of available recordings"""
        url = f"{self.base_url}/recordings"
        if path:
            url += f"?path={path}"
            
        response = requests.get(url)
        return response.json()
    
    def get_recording_file(self, filename, path=None):
        """Get a specific recording file"""
        url = f"{self.base_url}/recordings/{filename}"
        if path:
            url += f"?path={path}"
            
        response = requests.get(url, stream=True)
        return response
    
    def get_agent_history(self, filename, path=None):
        """Get a specific agent history file"""
        url = f"{self.base_url}/agent/history/{filename}"
        if path:
            url += f"?path={path}"
            
        response = requests.get(url)
        return response.json()
    
    def list_agent_history_files(self, path=None):
        """List all available agent history files"""
        url = f"{self.base_url}/agent/history-files"
        if path:
            url += f"?path={path}"
            
        response = requests.get(url)
        return response.json()
    
    def close_browser(self):
        """Close the browser instance"""
        response = requests.post(f"{self.base_url}/browser/close")
        return response.json()

    def test_video_paths(self):
        """Test function to verify video recording paths"""
        print("\n=== Testing Video Recording Paths ===")
        
        # Step 1: Get list of all recordings
        try:
            recordings = self.get_recordings()
            print(f"Found {len(recordings)} recordings")
            
            if not recordings:
                print("No recordings found. Cannot test video paths.")
                return
                
            # Print the first few recordings
            for i, recording in enumerate(recordings[:5]):
                print(f"Recording {i+1}: {recording}")
                
            # Step 2: Try to access the first recording
            if recordings and len(recordings) > 0:
                first_recording = recordings[0]
                recording_path = first_recording.get('path')
                recording_name = first_recording.get('name')
                
                if recording_name:
                    # Extract filename from the name (remove any numbering)
                    filename = recording_name.split('. ', 1)[-1] if '. ' in recording_name else recording_name
                    
                    print(f"\nTesting access to recording: {filename}")
                    response = self.get_recording_file(filename)
                    
                    if response.status_code == 200:
                        content_type = response.headers.get('Content-Type', '')
                        content_length = response.headers.get('Content-Length', '0')
                        print(f"Successfully accessed recording: {filename}")
                        print(f"Content-Type: {content_type}")
                        print(f"Content-Length: {content_length} bytes")
                    else:
                        print(f"Failed to access recording: {filename}")
                        print(f"Status code: {response.status_code}")
                        print(f"Response: {response.text[:200]}...")
        except Exception as e:
            print(f"Error testing video paths: {e}")
    
    def test_agent_history_video_links(self):
        """Test function to verify video links in agent history files"""
        print("\n=== Testing Agent History Video Links ===")
        
        try:
            # Step 1: Get list of all agent history files
            history_files = self.list_agent_history_files()
            files = history_files.get('files', [])
            
            print(f"Found {len(files)} agent history files")
            
            if not files:
                print("No agent history files found. Cannot test video links.")
                return
                
            # Print the first few history files
            for i, filename in enumerate(files[:5]):
                print(f"History file {i+1}: {filename}")
                
            # Step 2: Get the first history file
            if files and len(files) > 0:
                first_file = files[0]
                
                print(f"\nTesting agent history file: {first_file}")
                history_data = self.get_agent_history(first_file)
                
                # Step 3: Extract agent ID
                agent_id = history_data.get('agent_id')
                if not agent_id:
                    print("No agent ID found in history file")
                    return
                    
                print(f"Agent ID: {agent_id}")
                
                # Step 4: Check if a video exists for this agent ID
                video_filename = f"{agent_id}.webm"
                print(f"Checking for video file: {video_filename}")
                
                response = self.get_recording_file(video_filename)
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    content_length = response.headers.get('Content-Length', '0')
                    print(f"Successfully found video for agent: {agent_id}")
                    print(f"Content-Type: {content_type}")
                    print(f"Content-Length: {content_length} bytes")
                    print(f"Video URL: {self.base_url}/recordings/{video_filename}")
                else:
                    print(f"No video found for agent: {agent_id}")
                    print(f"Status code: {response.status_code}")
                    
                    # Try MP4 format as fallback
                    video_filename = f"{agent_id}.mp4"
                    print(f"Checking for alternative video file: {video_filename}")
                    
                    response = self.get_recording_file(video_filename)
                    if response.status_code == 200:
                        content_type = response.headers.get('Content-Type', '')
                        content_length = response.headers.get('Content-Length', '0')
                        print(f"Successfully found MP4 video for agent: {agent_id}")
                        print(f"Content-Type: {content_type}")
                        print(f"Content-Length: {content_length} bytes")
                        print(f"Video URL: {self.base_url}/recordings/{video_filename}")
                    else:
                        print(f"No MP4 video found for agent: {agent_id}")
                        print(f"Status code: {response.status_code}")
                        
                        # List all recordings to see what's available
                        recordings = self.get_recordings()
                        print("\nAvailable recordings:")
                        for recording in recordings:
                            print(f"- {recording.get('name', '')}")
        except Exception as e:
            print(f"Error testing agent history video links: {e}")

def main():
    # Construct default URL from environment variables
    default_base_url = os.getenv("API_BASE_URL", "http://localhost")
    default_base_port = os.getenv("API_BASE_PORT", "8000")
    
    # Remove any trailing slashes from the base_url
    default_base_url = default_base_url.rstrip('/')
    
    # Check if the base_url already includes a port
    parsed_url = urllib.parse.urlparse(default_base_url)
    
    if parsed_url.port:
        default_url = default_base_url
    else:
        default_url = f"{default_base_url}:{default_base_port}"
    
    parser = argparse.ArgumentParser(description="Browser Use API Client")
    parser.add_argument("--url", type=str, default=default_url, 
                        help=f"API base URL (default: {default_url})")
    
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
    
    # Test video paths command
    subparsers.add_parser("test-videos", help="Test video recording paths")
    
    # Test agent history video links command
    subparsers.add_parser("test-history-videos", help="Test video links in agent history files")
    
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
        if result and result.get("status") == "disabled":
            print("\nDeep search is disabled:")
            print(result.get("message", ""))
        elif result:
            print("\nDeep search completed:")
            print(f"Markdown content: {result.get('markdown_content', '')[:500]}...")
            print(f"File path: {result.get('file_path', '')}")
            
    elif args.command == "stop-search":
        result = client.stop_deep_search()
        if result.get("status") == "disabled":
            print("\nDeep search is disabled:")
            print(result.get("message", ""))
        else:
            print(json.dumps(result, indent=2))
        
    elif args.command == "recordings":
        result = client.get_recordings(args.path)
        print(json.dumps(result, indent=2))
        
    elif args.command == "close-browser":
        result = client.close_browser()
        print(json.dumps(result, indent=2))
        
    elif args.command == "test-videos":
        client.test_video_paths()
        
    elif args.command == "test-history-videos":
        client.test_agent_history_video_links()
        
    else:
        parser.print_help()
        
if __name__ == "__main__":
    main() 