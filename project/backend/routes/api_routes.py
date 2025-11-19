from flask import Blueprint, request, jsonify
import copy
import os
import base64
from werkzeug.utils import secure_filename
from services.ai_service import AIService
from services.comic_generator import ComicGenerator
from services.notification_service import NotificationService
from models import ComicDatabase
from config import Config
from data.missions_loader import (
    load_missions,
    get_mission_by_id,
    get_topic_by_id,
    build_progress_payload,
    get_unlocked_dares,
    get_next_dare
)

api_bp = Blueprint('api', __name__)

# Initialize services
ai_service = AIService()
comic_generator = ComicGenerator()
notification_service = NotificationService()
db = ComicDatabase(Config.DATABASE_URL)
missions_cache = load_missions()
mission_progress_store = {}
user_selfie_store = {}


def _get_user_mission_state(user_id, mission_id, create_if_missing=False):
    """Retrieve or initialize a user's mission progress entry."""
    if not user_id or not mission_id:
        return None

    user_store = mission_progress_store.setdefault(user_id, {})
    if mission_id not in user_store and create_if_missing:
        user_store[mission_id] = {
            'enrolled': True,
            'completed_topics': [],
            'claimed_dares': []
        }
    return user_store.get(mission_id)


def _serialize_mission_with_progress(mission, user_id=None):
    mission_payload = copy.deepcopy(mission)
    if user_id:
        user_state = _get_user_mission_state(user_id, mission.get('id'))
        mission_payload['progress'] = build_progress_payload(mission, user_state) if user_state else None
    else:
        mission_payload['progress'] = None
    return mission_payload


def _build_error(message, status_code=400):
    return jsonify({'error': message}), status_code


@api_bp.route('/missions', methods=['GET'])
def list_missions():
    """Return mission catalog with optional user progress."""
    user_id = request.args.get('user_id')
    missions = [_serialize_mission_with_progress(mission, user_id) for mission in missions_cache]
    return jsonify({'missions': missions})


@api_bp.route('/missions/enroll', methods=['POST'])
def enroll_in_mission():
    data = request.get_json() or {}
    user_id = data.get('user_id')
    mission_id = data.get('mission_id')

    if not user_id or not mission_id:
        return _build_error('user_id and mission_id are required')

    mission = get_mission_by_id(mission_id)
    if not mission:
        return _build_error('Mission not found', 404)

    state = _get_user_mission_state(user_id, mission_id, create_if_missing=True)
    state['enrolled'] = True

    progress_payload = build_progress_payload(mission, state)
    notification_service.notify_enrollment(user_id, mission.get('title', 'a mission'))
    if progress_payload.get('next_topic'):
        notification_service.notify_next_topic(
            user_id,
            mission.get('title', 'a mission'),
            progress_payload['next_topic'].get('title')
        )

    return jsonify({
        'mission': mission,
        'progress': progress_payload
    })


@api_bp.route('/missions/<mission_id>/next-topic', methods=['GET'])
def get_next_mission_topic(mission_id):
    user_id = request.args.get('user_id')
    if not user_id:
        return _build_error('user_id is required')

    mission = get_mission_by_id(mission_id)
    if not mission:
        return _build_error('Mission not found', 404)

    state = _get_user_mission_state(user_id, mission_id)
    if not state or not state.get('enrolled'):
        return _build_error('User is not enrolled in this mission', 403)

    progress_payload = build_progress_payload(mission, state)
    next_topic = progress_payload.get('next_topic')
    if next_topic:
        notification_service.notify_next_topic(
            user_id,
            mission.get('title', 'a mission'),
            next_topic.get('title')
        )

    return jsonify({
        'mission_id': mission_id,
        'next_topic': next_topic,
        'progress': progress_payload
    })


@api_bp.route('/missions/complete-step', methods=['POST'])
def complete_mission_step():
    data = request.get_json() or {}
    user_id = data.get('user_id')
    mission_id = data.get('mission_id')
    topic_id = data.get('topic_id')

    if not user_id or not mission_id or not topic_id:
        return _build_error('user_id, mission_id and topic_id are required')

    mission = get_mission_by_id(mission_id)
    if not mission:
        return _build_error('Mission not found', 404)

    topic = get_topic_by_id(mission, topic_id)
    if not topic:
        return _build_error('Topic does not belong to mission', 400)

    state = _get_user_mission_state(user_id, mission_id)
    if not state or not state.get('enrolled'):
        return _build_error('User is not enrolled in this mission', 403)

    if topic_id not in state['completed_topics']:
        state['completed_topics'].append(topic_id)

    progress_payload = build_progress_payload(mission, state)
    if progress_payload.get('is_complete'):
        notification_service.notify_mission_completed(user_id, mission.get('title', 'a mission'))
    elif progress_payload.get('next_topic'):
        notification_service.notify_next_topic(
            user_id,
            mission.get('title', 'a mission'),
            progress_payload['next_topic'].get('title')
        )

    return jsonify({
        'mission_id': mission_id,
        'completed_topic': topic,
        'progress': progress_payload
    })

@api_bp.route('/missions/claim-dare', methods=['POST'])
def claim_dare():
    data = request.get_json() or {}
    user_id = data.get('user_id')
    mission_id = data.get('mission_id')
    dare_id = data.get('dare_id')

    if not user_id or not mission_id or not dare_id:
        return _build_error('user_id, mission_id and dare_id are required')

    mission = get_mission_by_id(mission_id)
    if not mission:
        return _build_error('Mission not found', 404)

    state = _get_user_mission_state(user_id, mission_id)
    if not state or not state.get('enrolled'):
        return _build_error('User is not enrolled in this mission', 403)

    completed_count = len(state.get('completed_topics', []))
    unlocked_dares = get_unlocked_dares(mission, completed_count)
    
    dare = None
    for d in unlocked_dares:
        if d.get('id') == dare_id:
            dare = d
            break
    
    if not dare:
        return _build_error('Dare not unlocked yet or does not exist', 400)

    if 'claimed_dares' not in state:
        state['claimed_dares'] = []
    
    if dare_id not in state['claimed_dares']:
        state['claimed_dares'].append(dare_id)

    progress_payload = build_progress_payload(mission, state)
    notification_service.send_push_notification(
        user_id, 
        'Dare Claimed!', 
        f"Parent must complete: {dare.get('title')}"
    )

    return jsonify({
        'mission_id': mission_id,
        'claimed_dare': dare,
        'progress': progress_payload
    })

@api_bp.route('/generate-comic', methods=['POST'])
def generate_comic():
    """Generate comic API"""
    try:
        data = request.get_json()
        topic = data.get('topic', '').strip()
        age_group = data.get('age_group', '6-8')
        image_style = data.get('image_style', '<anime>')
        
        if not topic:
            return jsonify({'error': 'Please enter a valid topic'}), 400
        
        if age_group not in Config.AGE_GROUPS:
            return jsonify({'error': 'Invalid age group'}), 400
        
        # Validate style parameter
        valid_styles = ['<3d cartoon>', '<anime>', '<oil painting>', '<watercolor>', 
                       '<sketch>', '<chinese painting>', '<flat illustration>', 
                       '<photography>', '<portrait>', '<auto>']
        if image_style not in valid_styles:
            image_style = '<anime>'  # Default to anime style
        
        print(f"Generating comic - Topic: {topic}, Age Group: {age_group}, Style: {image_style}")
        
        user_id = data.get('user_id')
        character_description = data.get('character_description')
        if not character_description and user_id:
            character_description = user_selfie_store.get(user_id, {}).get('character_description')
        
        # Generate tutorial steps with optional character description
        steps = ai_service.generate_tutorial_steps(topic, age_group, character_description)
        
        if not steps:
            return jsonify({'error': 'Unable to generate tutorial steps'}), 500
        
        # Save to database
        comic_id = db.save_comic(topic, age_group, steps)
        
        # Generate comic (pass style parameter and topic for content-first prompts)
        comic_path = comic_generator.create_comic(steps, comic_id, image_style, topic)
        
        # Verify file exists
        if not comic_path or not os.path.exists(comic_path):
            print(f" Comic file not generated: {comic_path}")
            return jsonify({'error': 'Comic file generation failed'}), 500
        
        # Get file info for debugging
        file_size = os.path.getsize(comic_path)
        print(f" Comic generated: {comic_path} ({file_size/1024:.2f} KB)")
        
        # Build URLs for each panel
        panel_urls = []
        for i in range(len(steps)):
            panel_url = f'/static/generated_comics/comic_{comic_id}_panel_{i}.png'
            panel_urls.append(panel_url)
        
        # Build final comic URL
        comic_url = f'/static/generated_comics/comic_{comic_id}_final.png'
        print(f" Returning {len(panel_urls)} panels and 1 complete comic")
        
        return jsonify({
            'success': True,
            'comic_id': comic_id,
            'steps': steps,
            'comic_url': comic_url,
            'panel_urls': panel_urls  # Added: URLs for each panel
        })
        
    except Exception as e:
        print(f"Comic generation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'An error occurred while generating the comic'}), 500

@api_bp.route('/comic/<int:comic_id>')
def get_comic(comic_id):
    """Get comic information"""
    try:
        comic = db.get_comic(comic_id)
        
        if not comic:
            return jsonify({'error': 'Comic does not exist'}), 404
        
        return jsonify({
            'success': True,
            'comic': comic
        })
        
    except Exception as e:
        print(f"Get comic error: {e}")
        return jsonify({'error': 'An error occurred while retrieving the comic'}), 500

@api_bp.route('/upload-selfie', methods=['POST'])
def upload_selfie():
    """Upload selfie and generate character description"""
    try:
        if 'selfie' not in request.files:
            return jsonify({'error': 'No selfie file provided'}), 400
        
        file = request.files['selfie']
        user_id = request.form.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file:
            filename = secure_filename(file.filename)
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            project_root = os.path.dirname(backend_dir)
            upload_dir = os.path.join(project_root, 'frontend', 'static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            
            filepath = os.path.join(upload_dir, f"{user_id}_{filename}")
            file.save(filepath)
            
            character_description = ai_service.generate_character_from_selfie(filepath)
            
            user_selfie_store[user_id] = {
                'filepath': filepath,
                'character_description': character_description
            }
            
            return jsonify({
                'success': True,
                'character_description': character_description,
                'message': 'Selfie uploaded successfully'
            })
    
    except Exception as e:
        print(f"Selfie upload error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to upload selfie'}), 500

@api_bp.route('/notifications', methods=['GET'])
def get_notifications():
    """Get user notifications"""
    try:
        user_id = request.args.get('user_id')
        notif_type = request.args.get('type', 'email')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        all_notifications = notification_service.sent_notifications
        user_notifications = [
            n for n in all_notifications 
            if n.get('user_id') == user_id and n.get('type') == notif_type
        ]
        
        user_notifications.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'notifications': user_notifications
        })
    
    except Exception as e:
        print(f"Get notifications error: {e}")
        return jsonify({'error': 'Failed to retrieve notifications'}), 500

@api_bp.route('/health')
def health_check():
    """Health check API"""
    return jsonify({'status': 'healthy', 'message': 'StorySpark API is running normally'})
