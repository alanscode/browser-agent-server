import json
import os
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional

def generate_cypress_test(agent_history_path: str, output_dir: str = None) -> str:
    """
    Analyzes the agent history and generates a Cypress test script based on the interacted elements.
    
    Args:
        agent_history_path: Path to the agent history JSON file
        output_dir: Directory where the Cypress test script will be saved
        
    Returns:
        Path to the generated Cypress test script
    """
    # Use top-level cypress/e2e folder if output_dir is not specified
    if output_dir is None:
        # Get the project root directory (3 levels up from this file)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        output_dir = os.path.join(project_root, "generated-cypress")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Load agent history
    with open(agent_history_path, 'r') as f:
        agent_history = json.load(f)
    
    # Extract the original prompt to use as test description
    original_prompt = agent_history.get('original_prompt', 'Agent test')
    
    # Generate a timestamp for the filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_name = "agent_test_" + timestamp + ".cy.js"
    output_path = os.path.join(output_dir, test_name)
    
    # Generate the test script content
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    test_script = []
    test_script.append("// Cypress test generated from agent history")
    test_script.append("// Original prompt: " + original_prompt)
    test_script.append("// Generated at: " + current_time)
    test_script.append("// Note: This test may fail if Google shows a CAPTCHA challenge")
    test_script.append("")
    test_script.append("describe('Agent Test', () => {")
    test_script.append("  it('" + original_prompt.replace("'", "\\'") + "', () => {")
    
    # Process each step in the agent history
    for step in agent_history.get('history', []):
        actions = _extract_actions(step)
        for action in actions:
            if action:
                test_script.append("    " + action)
    
    # Close the test
    test_script.append("  })")
    test_script.append("})")
    test_script.append("")
    
    # Write the test script to file
    with open(output_path, 'w') as f:
        f.write('\n'.join(test_script))
    
    print("Generated Cypress test: " + output_path)
    return output_path

def _extract_actions(step: Dict[str, Any]) -> List[str]:
    """
    Extracts Cypress commands from a step in the agent history.
    
    Args:
        step: A step from the agent history
        
    Returns:
        List of Cypress commands
    """
    actions = []
    
    # Extract model output actions
    model_actions = step.get('model_output', {}).get('action', [])
    
    for action in model_actions:
        # Handle URL navigation
        if 'go_to_url' in action:
            url = action['go_to_url']['url']
            actions.append("cy.visit('" + url + "')")
            # Add a comment about potential CAPTCHA
            actions.append("// If Google shows a CAPTCHA challenge, the test will fail")
        
        # Handle text input
        elif 'input_text' in action:
            index = action['input_text'].get('index')
            text = action['input_text'].get('text')
            
            # Get the interacted element details
            element_details = _get_element_details(step, index)
            if element_details:
                selector = _get_best_selector(element_details)
                # Escape single quotes in the selector
                selector = selector.replace("'", "\\'")
                actions.append("cy.get('" + selector + "').type('" + text + "')")
        
        # Handle element clicks
        elif 'click_element' in action:
            index = action['click_element'].get('index')
            
            # Get the interacted element details
            element_details = _get_element_details(step, index)
            if element_details:
                selector = _get_best_selector(element_details)
                # Escape single quotes in the selector
                selector = selector.replace("'", "\\'")
                
                # For the Google Search button, we need to handle it differently
                # because there are multiple buttons with the same selector
                if "btnK" in selector:
                    # Add a wait for the button to be visible and force the click
                    actions.append("cy.get('" + selector + "').first().should('be.visible').click({force: true})")
                else:
                    actions.append("cy.get('" + selector + "').click()")
    
    return actions

def _get_element_details(step: Dict[str, Any], index: Optional[int]) -> Optional[Dict[str, Any]]:
    """
    Gets the details of an interacted element from the step.
    
    Args:
        step: A step from the agent history
        index: The index of the interacted element
        
    Returns:
        Details of the interacted element, or None if not found
    """
    if index is None:
        return None
    
    interacted_elements = step.get('state', {}).get('interacted_element', [])
    
    # Find the element with the matching highlight_index
    for element in interacted_elements:
        if element and element.get('highlight_index') == index:
            return element
    
    return None

def _get_best_selector(element: Dict[str, Any]) -> str:
    """
    Gets the best CSS selector for an element.
    
    Args:
        element: Details of an element
        
    Returns:
        CSS selector for the element
    """
    # Try to use ID if available
    if element.get('attributes', {}).get('id'):
        return "#" + element['attributes']['id']
    
    # Try to use a combination of tag name and attributes
    tag_name = element.get('tag_name', '')
    attributes = element.get('attributes', {})
    
    # Build a more specific selector using multiple attributes when available
    selector_parts = []
    
    # Always include the tag name
    selector_parts.append(tag_name)
    
    # Add attributes to make the selector more specific
    if 'name' in attributes:
        selector_parts.append("[name='" + attributes['name'] + "']")
    
    if 'class' in attributes:
        # Use the first class in the class list
        class_name = attributes['class'].split()[0]
        selector_parts.append("." + class_name)
    
    if 'aria-label' in attributes:
        selector_parts.append("[aria-label='" + attributes['aria-label'] + "']")
    
    if 'type' in attributes:
        selector_parts.append("[type='" + attributes['type'] + "']")
    
    if 'role' in attributes:
        selector_parts.append("[role='" + attributes['role'] + "']")
    
    # Combine all parts into a single selector
    if selector_parts:
        return ''.join(selector_parts)
    
    # Fall back to the provided CSS selector if available
    if element.get('css_selector'):
        # Simplify the selector to make it more robust
        simplified = element['css_selector'].split(' > ')[-1]
        return simplified
    
    # Last resort: use XPath
    if element.get('xpath'):
        return element['xpath']
    
    # If all else fails, return a generic selector
    return tag_name

def run_cypress_test(test_path: str, headless: bool = True) -> None:
    """
    Runs a Cypress test.
    
    Args:
        test_path: Path to the Cypress test script
        headless: Whether to run the test in headless mode
    """
    # Get the project root directory (where cypress.config.js is located)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    # Make sure we're in the project root directory
    current_dir = os.getcwd()
    os.chdir(project_root)
    
    try:
        # Run the Cypress test
        mode = "--headless" if headless else ""
        cmd = f"npx cypress run {mode} --spec {test_path}"
        print(f"Running command: {cmd} from directory: {os.getcwd()}")
        subprocess.run(cmd, shell=True)
    finally:
        # Change back to the original directory
        os.chdir(current_dir)

if __name__ == "__main__":
    # Example usage
    test_path = generate_cypress_test("browser-agent-server/tmp/agent_history/test.json")
    # Uncomment to run the test
    # run_cypress_test(test_path)
