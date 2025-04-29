#!/usr/bin/env python3
"""
build_timeline_data.py

Convert a provenance dictionary into groups and items suitable
for a vis-timeline swimlane view.
"""
from typing import Dict, List, Tuple

def build_timeline_data(provenance: Dict) -> Tuple[List[Dict], List[Dict]]:
    """
    Build groups and items for a timeline visualization.

    Args:
        provenance: dict from proof_of_work JSON under 'provenance'.

    Returns:
        groups: list of dicts with keys 'id' and 'content' for each agent.
        items: list of dicts with keys 'id', 'group', 'content', 'start'.
    """
    groups = []
    items = []
    # Root agent
    root = provenance.get('root_agent', {})
    root_name = root.get('name', 'root')
    groups.append({'id': root_name, 'content': root_name})
    for step in root.get('steps', []):
        seq = step.get('sequence')
        step_type = step.get('type', '')
        item_id = f"{root_name}-step-{seq}"
        items.append({
            'id': item_id,
            'group': root_name,
            'content': step_type,
            'start': seq
        })
    # Managed agents
    for ma in provenance.get('managed_agents', {}).values():
        name = ma.get('name')
        if not name:
            continue
        groups.append({'id': name, 'content': name})
        for step in ma.get('steps', []):
            seq = step.get('sequence')
            step_type = step.get('type', '')
            item_id = f"{name}-step-{seq}"
            items.append({
                'id': item_id,
                'group': name,
                'content': step_type,
                'start': seq
            })
    return groups, items