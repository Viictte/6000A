import json
import re
import requests
from config import Config


class AIService:
    """AI service for generating tutorial steps"""

    def __init__(self):
        self.api_key = Config.DASHSCOPE_API_KEY
        self.api_url = Config.DASHSCOPE_TEXT_API

    def generate_tutorial_steps(self, topic, age_group):
        """Generate tutorial steps in English"""
        age_config = Config.AGE_GROUPS[age_group]
        words_per_step = age_config['words_per_step']

        character_profile = self._select_character_template(topic, age_group)
        topic_brief = self._build_topic_brief(topic, age_group)
        prompt = self._build_prompt(topic, age_group, words_per_step,
                                    character_profile, topic_brief)

        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            payload = {
                "model": "qwen-turbo",
                "input": {
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an AI assistant specialized in creating tutorials for children. Always respond in English only."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                },
                "parameters": {
                    "max_tokens": 500,
                    "temperature": 0.6
                }
            }

            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200:
                result = response.json()
                if 'output' in result and 'text' in result['output']:
                    content = result['output']['text']
                    structured_steps = self._parse_structured_response(content)

                    if not structured_steps:
                        structured_steps = self._parse_legacy_steps(content)

                    if structured_steps:
                        character_description = self._generate_character_description(
                            age_group, character_profile)

                        for i, step in enumerate(structured_steps):
                            step['character_description'] = character_description
                            if not step.get('action_scene'):
                                step['action_scene'] = self._generate_action_scene(step, topic, i)

                        return structured_steps

            print(f"API call failed: {response.status_code}, {response.text}")
            return self._get_fallback_steps(topic)

        except Exception as e:
            print(f"AI service error: {e}")
            return self._get_fallback_steps(topic)

    def _parse_structured_response(self, content):
        """Parse JSON-like structured output"""
        try:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start == -1 or json_end == -1:
                return None

            json_text = content[json_start:json_end]
            data = json.loads(json_text)
            steps_data = data.get('steps', [])
            steps = []

            for step in steps_data:
                title = step.get('title') or step.get('heading') or 'Step'
                description = step.get('instruction') or step.get('description') or ''
                action_scene = step.get('panel_prompt') or step.get('visual_action')
                emoji = step.get('emoji', '✨')
                if not description:
                    continue

                steps.append({
                    'title': f"{emoji} {title.strip()}",
                    'description': description.strip(),
                    'action_scene': action_scene.strip() if action_scene else None
                })

            return steps if steps else None
        except Exception:
            return None

    def _parse_legacy_steps(self, content):
        """Parse simple step output when structured format fails"""
        steps = []
        lines = content.strip().split('\n')

        for line in lines:
            line = line.strip()
            if line and ('Step' in line or 'step' in line):
                match = re.search(r'(.+?)\s*[-:]\s*(.+)', line)
                if match:
                    title = match.group(1).strip()
                    description = match.group(2).strip()
                    steps.append({
                        'title': title,
                        'description': description
                    })

        return steps

    def _generate_character_description(self, age_group, character_profile=None):
        """Generate consistent character description"""
        if not character_profile:
            return (
                "A cute cartoon child character with big expressive eyes, friendly smile, wearing "
                f"casual t-shirt and shorts, child-friendly art style suitable for {age_group} years old"
            )

        return (
            f"{character_profile['visual']}, bright colors, friendly smile, matching outfit, age appropriate for {age_group} years old"
        )

    def _build_prompt(self, topic, age_group, words_per_step, character_profile, topic_brief):
        """Create a detailed prompt to keep characters and actions consistent"""
        return f"""
You are KidSpark, an assistant who writes clear storyboards for child-friendly tutorial comics.
Always respond in valid JSON only.

Character to feature in EVERY panel:
Name: {character_profile['name']}
Visual style: {character_profile['visual']}
Personality: {character_profile['personality']}
Catchphrase or encouragements should match the personality.

Age group: {age_group}
Topic brief:
{topic_brief}

Create 3-5 ordered steps (each <= {words_per_step} English words) that help a child accomplish the topic.
Each step must include a precise action the character performs so that an illustrator can keep poses consistent.

Return JSON EXACTLY in this shape:
{{
  "steps": [
    {{
      "title": "Short heading",
      "instruction": "Child friendly explanation",
      "panel_prompt": "Dynamic description mentioning {character_profile['name']} performing the action",
      "emoji": "encouraging emoji"
    }}
  ]
}}

Only output JSON. Do not include markdown fences.
"""

    def _build_topic_brief(self, topic, age_group):
        """Create extra context so the LLM understands the goal"""
        topic_lower = topic.lower()
        context = []
        materials = []
        focus_actions = []

        keyword_map = {
            'brush': ('Morning routine in the bathroom', ['toothbrush', 'toothpaste', 'cup'], ['brush gently', 'rinse mouth']),
            'math': ('Learning numbers with manipulatives', ['paper', 'pencil', 'counters'], ['count out loud', 'check answers']),
            'read': ('Quiet reading corner with cushions', ['favorite book', 'bookmark'], ['sound out words', 'turn pages carefully']),
            'homework': ('Study desk with good light', ['notebook', 'pencils', 'timer'], ['plan tasks', 'take breaks']),
            'cook': ('Kid-safe kitchen helper station', ['mixing bowl', 'spoon', 'apron'], ['measure safely', 'stir slowly']),
            'share': ('Playroom with classmates or siblings', ['toy bin'], ['offer turns', 'use kind words']),
            'clean': ('Tidy-up time in bedroom or classroom', ['basket', 'cloth'], ['sort toys', 'wipe surfaces'])
        }

        for keyword, (scene, items, actions) in keyword_map.items():
            if keyword in topic_lower:
                context.append(scene)
                materials.extend(items)
                focus_actions.extend(actions)

        if not context:
            context.append('Friendly everyday environment that feels safe and encouraging')

        if not materials:
            materials = ['simple household items']

        if not focus_actions:
            focus_actions = ['show clear start, middle, and finish']

        return (
            f"Topic: {topic}\n"
            f"Age focus: {age_group} years\n"
            f"Helpful setting: {', '.join(context)}\n"
            f"Helpful props: {', '.join(materials)}\n"
            f"Key actions to highlight: {', '.join(focus_actions)}"
        )

    def _select_character_template(self, topic, age_group):
        """Pick a deterministic character template based on topic"""
        templates = [
            {
                'name': 'Sunny Scout',
                'visual': 'cheerful kid hero with star hoodie, round cheeks, bright sneakers, curly hair',
                'personality': 'optimistic, encouraging, always explains why each action matters'
            },
            {
                'name': 'Luna Spark',
                'visual': 'curious girl with twin buns, galaxy backpack, pastel jumper, expressive eyes',
                'personality': 'playful problem-solver who loves playful sound effects'
            },
            {
                'name': 'Max Builder',
                'visual': 'inventive boy wearing utility vest, goggles on head, comfy jeans and sneakers',
                'personality': 'hands-on helper who narrates each motion step-by-step'
            },
            {
                'name': 'Ami Artist',
                'visual': 'gentle child with painter apron, oversized beret, colorful wristbands',
                'personality': 'imaginative storyteller who cheers kids on with kind words'
            }
        ]

        seed = sum(ord(c) for c in (topic.lower() + age_group))
        template = templates[seed % len(templates)]
        return template

    def _generate_action_scene(self, step, topic, step_index):
        """Generate dynamic action scene description based on step content"""
        description = step['description'].lower()

        # Map keywords to action scenes
        action_scenes = {
            # Hygiene & Self-care
            'brush': 'actively brushing teeth with toothbrush, showing motion, bathroom sink background',
            'wash': 'washing with soap and water, bubbles visible, hands in motion',
            'clean': 'cleaning motion, circular movements, concentrated face',
            'rinse': 'rinsing mouth with water, head tilted, water droplets visible',
            'comb': 'combing hair carefully, looking in mirror, neat appearance',
            'bath': 'taking bath or shower, enjoying water, happy expression',
            'towel': 'drying with towel, wrapping up, cozy feeling',

            # Dressing & Grooming
            'wear': 'putting on clothes, adjusting fit, looking in mirror',
            'dress': 'getting dressed, choosing outfit, proud expression',
            'button': 'fastening buttons, careful finger movements, focused',
            'zip': 'zipping up jacket, pulling up slowly, determined face',
            'tie': 'tying shoes or bows, concentrated on knot-making',
            'fold': 'folding clothes neatly, organized stacking, tidy arrangement',

            # Eating & Mealtime
            'eat': 'eating food happily, using utensils, enjoying meal',
            'drink': 'drinking from cup, swallowing, refreshed expression',
            'pour': 'pouring liquid carefully, steady hands, focused',
            'cut': 'cutting food with knife, safety-conscious, adult supervision',
            'cook': 'helping with cooking, mixing ingredients, chef hat',
            'set': 'setting table, arranging plates and utensils, organized',

            # School & Learning
            'read': 'reading book, turning pages, engaged expression',
            'write': 'writing with pencil, forming letters, concentrated',
            'draw': 'drawing on paper, creative expression, colorful markers',
            'color': 'coloring inside lines, selecting colors, artistic',
            'count': 'counting objects, using fingers, learning numbers',
            'spell': 'spelling words, sounding out letters, thinking face',

            # Play & Activities
            'play': 'playing with toys, happy expression, interactive',
            'build': 'building with blocks, stacking carefully, creative',
            'share': 'sharing toys with friends, generous gesture, smiling',
            'run': 'running actively, movement blur, energetic pose',
            'jump': 'jumping joyfully, mid-air action, excited expression',
            'catch': 'catching ball, hands ready, focused eyes',

            # Home & Chores
            'tidy': 'tidying up room, putting toys away, organized space',
            'make': 'making bed, smoothing sheets, neat arrangement',
            'sweep': 'sweeping floor, using broom, cleaning motion',
            'water': 'watering plants, caring for nature, gentle pouring',
            'feed': 'feeding pet, caring for animal, loving interaction',

            # Social & Emotions
            'share': 'sharing with others, generous hands, friendly smile',
            'help': 'helping someone, supportive gesture, kind expression',
            'listen': 'listening carefully, attentive ears, focused face',
            'wait': 'waiting patiently, calm expression, understanding',
            'sorry': 'apologizing sincerely, remorseful but hopeful face',
            'thank': 'thanking someone, grateful expression, polite bow',

            # Technology & Modern
            'click': 'using computer mouse, focused on screen, learning',
            'type': 'typing on keyboard, careful fingers, digital literacy',
            'swipe': 'using tablet, swipe gestures, interactive learning',

            # General Actions
            'grab': 'reaching out and grabbing object with both hands, excited expression',
            'hold': 'holding item confidently, showing to viewer',
            'apply': 'applying or using item, focused expression, hands in action',
            'scrub': 'scrubbing motion with hands, soap suds, active movement',
            'dry': 'drying with towel, wiping motion',
            'get ready': 'preparing items, standing confidently, items visible',
            'prepare': 'organizing items on surface, focused expression',
            'smile': 'big happy smile showing teeth, proud expression, thumbs up'
        }

        # Find matching action
        scene = None
        for keyword, action in action_scenes.items():
            if keyword in description:
                scene = action
                break

        # Default scene if no match
        if not scene:
            scenes_by_step = [
                'holding and showing items, standing confidently',
                'performing the action, hands in motion, focused expression',
                'continuing the task, active movement, engaged face',
                'completing the step, satisfied expression',
                'celebrating completion, happy smile, thumbs up'
            ]
            scene = scenes_by_step[min(step_index, len(scenes_by_step)-1)]

        return scene

    def _get_fallback_steps(self, topic):
        """Fallback steps in English"""
        return [
            {
                'title': ' Get Ready',
                'description': f"Let's learn about {topic}!",
                'character_description': 'A cute cartoon child with big eyes, casual clothes',
                'action_scene': 'standing confidently, holding items, ready to start'
            },
            {
                'title': ' Step One',
                'description': 'Follow the instructions to begin',
                'character_description': 'A cute cartoon child with big eyes, casual clothes',
                'action_scene': 'starting the action, hands in motion, focused'
            },
            {
                'title': ' Keep Going',
                'description': 'Great! Continue to the next step',
                'character_description': 'A cute cartoon child with big eyes, casual clothes',
                'action_scene': 'performing the task, active movement'
            },
            {
                'title': ' All Done',
                'description': 'Awesome! You did it!',
                'character_description': 'A cute cartoon child with big eyes, casual clothes',
                'action_scene': 'celebrating, big smile, thumbs up'
            }
        ]
