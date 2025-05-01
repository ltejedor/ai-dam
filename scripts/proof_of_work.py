import os
import json
from datetime import datetime

def extract_tool_calls(agent):
    """
    Extract tool calls from an agent's memory steps.

    Args:
        agent: Agent instance with memory attribute (e.g., smolagents CodeAgent).

    Returns:
        List of tool call dictionaries representing each function call made by the agent.
    """
    memory = getattr(agent, 'memory', None)
    if memory is None:
        raise ValueError("Agent has no memory attribute")
    # Try succinct steps, then full steps, then direct steps list
    if hasattr(memory, 'get_succinct_steps'):
        steps = memory.get_succinct_steps()
    elif hasattr(memory, 'get_full_steps'):
        steps = memory.get_full_steps()
    else:
        steps = []
        for step in getattr(memory, 'steps', []):
            if hasattr(step, 'dict'):
                steps.append(step.dict())
    # Collect tool_calls
    calls = []
    for step in steps:
        tool_calls = step.get('tool_calls') or []
        for call in tool_calls:
            calls.append(call)
    return calls

def save_proof_of_work(agent, output_dir='output', prefix='proof_of_work'):
    """
    Save detailed proof of work (provenance) including tasks, steps, tool calls,
    observations, and final answer for the agent and any managed agents.

    Args:
        agent: Agent instance with recorded memory of steps.
        output_dir: Directory path to save the output file (will be created if not exists).
        prefix: Filename prefix for the proof of work file.

    Returns:
        The path to the saved JSON file.
    """
    import os, json
    from datetime import datetime
    # Import step types for isinstance checks
    from smolagents.memory import TaskStep, PlanningStep, ActionStep, SystemPromptStep, FinalAnswerStep

    os.makedirs(output_dir, exist_ok=True)

    def convert_step(step, agent_name, sequence):
        # Base record with agent identity and sequence order
        record = {
            "agent": agent_name,
            "sequence": sequence,
        }
        # Capture step-specific details
        if isinstance(step, SystemPromptStep):
            record.update({
                "type": "system_prompt",
                "system_prompt": step.system_prompt,
            })
        elif isinstance(step, TaskStep):
            record.update({
                "type": "task",
                "task": step.task,
            })
        elif isinstance(step, PlanningStep):
            record.update({
                "type": "planning",
                "plan": step.plan,
            })
        elif isinstance(step, ActionStep):
            calls = [tc.dict() for tc in (step.tool_calls or [])]
            record.update({
                "type": "action",
                "step_number": step.step_number,
                "model_output": step.model_output,
                "tool_calls": calls,
                "observations": step.observations,
                "action_output": step.action_output,
                "start_time": step.start_time,
                "end_time": step.end_time,
                "duration": step.duration,
            })
        elif isinstance(step, FinalAnswerStep):
            record.update({
                "type": "final_answer",
                "final_answer": step.final_answer,
            })
        else:
            # Fallback for unknown step types
            record.update({
                "type": "unknown",
                "data": getattr(step, 'dict', lambda: {})(),
            })
        return record

    def extract_agent_records(agent_obj):
        # Determine agent identity
        agent_name = getattr(agent_obj, 'name', None) or getattr(agent_obj, 'agent_name', type(agent_obj).__name__)
        steps = getattr(agent_obj.memory, 'steps', []) or []
        records = []
        for idx, step in enumerate(steps):
            records.append(convert_step(step, agent_name, idx))
        return agent_name, records

    # Build structured provenance
    provenance = {}
    # Root agent entry
    root_name, root_records = extract_agent_records(agent)
    provenance['root_agent'] = {
        'name': root_name,
        'class': type(agent).__name__,
        'model': getattr(getattr(agent, 'model', None), 'model_id', None),
        'steps': root_records,
    }
    # Managed agents entries
    managed_agents = {}
    for name, sub_agent in getattr(agent, 'managed_agents', {}).items():
        sub_name, sub_records = extract_agent_records(sub_agent)
        managed_agents[sub_name] = {
            'name': sub_name,
            'class': type(sub_agent).__name__,
            'model': getattr(getattr(sub_agent, 'model', None), 'model_id', None),
            'steps': sub_records,
        }
    if managed_agents:
        provenance['managed_agents'] = managed_agents

    # Write to file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{prefix}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({"run_id": timestamp, "provenance": provenance}, f, indent=2)
    return filepath
