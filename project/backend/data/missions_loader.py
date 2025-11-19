"""Utilities to load and query mission metadata."""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Dict, List, Optional

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
MISSIONS_FILE = os.path.join(DATA_DIR, 'missions.json')


class MissionNotFoundError(KeyError):
    """Raised when a mission cannot be found in the metadata file."""


@lru_cache(maxsize=1)
def load_missions() -> List[Dict]:
    """Load the static mission metadata JSON file.

    Returns:
        A list of mission dictionaries containing topic metadata.
    """
    if not os.path.exists(MISSIONS_FILE):
        raise FileNotFoundError(f"Mission metadata file not found: {MISSIONS_FILE}")

    with open(MISSIONS_FILE, 'r', encoding='utf-8') as missions_file:
        return json.load(missions_file)


def get_mission_by_id(mission_id: str) -> Optional[Dict]:
    """Retrieve a single mission definition by its identifier."""
    if not mission_id:
        return None

    for mission in load_missions():
        if mission.get('id') == mission_id:
            return mission
    return None


def get_topic_by_id(mission: Dict, topic_id: str) -> Optional[Dict]:
    """Find a topic definition within a mission."""
    if not mission or not topic_id:
        return None

    for topic in mission.get('topics', []):
        if topic.get('id') == topic_id:
            return topic
    return None


def build_progress_payload(mission: Dict, state: Dict) -> Dict:
    """Construct a normalized progress payload for API responses."""
    topics = mission.get('topics', [])
    total_topics = len(topics)
    completed_topics = list(state.get('completed_topics', [])) if state else []
    completed_count = len(completed_topics)

    next_topic = None
    for topic in topics:
        if topic.get('id') not in completed_topics:
            next_topic = topic
            break

    is_complete = total_topics > 0 and completed_count >= total_topics

    return {
        'mission_id': mission.get('id'),
        'enrolled': bool(state.get('enrolled')) if state else False,
        'completed_topics': completed_topics,
        'completed_count': completed_count,
        'total_topics': total_topics,
        'next_topic': next_topic,
        'is_complete': is_complete
    }
