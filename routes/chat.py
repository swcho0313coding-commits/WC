from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from utils.csv_manager import CSVManager
from utils.auth import login_required
from datetime import datetime
import uuid

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/')
@login_required
def index():
    # Chat tab (Rooms list)
    rooms = CSVManager.read('data/chat_rooms.csv')
    username = session['user']['name']

    user_rooms = []
    for r in rooms:
        if r['type'] == 'global' or username in r['members'].split(','):
            user_rooms.append(r)

    return render_template('chat/index.html', rooms=user_rooms, active_tab='chat')

@chat_bp.route('/contacts')
@login_required
def contacts():
    # Friends tab (Users list based on phone numbers or entire citizens)
    users = CSVManager.read('data/users.csv')
    # Filter out pending/deleted users
    active_citizens = [u for u in users if u['status'] == 'active' and u['name'] != session['user']['name']]
    return render_template('chat/contacts.html', users=active_citizens, active_tab='contacts')

@chat_bp.route('/start_dm/<target_name>', methods=['POST'])
@login_required
def start_dm(target_name):
    # Check if DM already exists
    rooms = CSVManager.read('data/chat_rooms.csv')
    my_name = session['user']['name']

    # Simple check for DM room with these two members
    existing_room = None
    for r in rooms:
        if r['type'] == 'private':
            members = set(r['members'].split(','))
            if members == {my_name, target_name}:
                existing_room = r
                break

    if existing_room:
        return redirect(url_for('chat.room', room_id=existing_room['room_id']))

    # Create new DM
    room_id = f"dm_{uuid.uuid4().hex[:8]}"
    new_room = {
        'room_id': room_id,
        'type': 'private',
        'name': f"{target_name}",
        'members': f"{my_name},{target_name}",
        'last_message': '대화를 시작했습니다.',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    CSVManager.append('data/chat_rooms.csv', new_room, ['room_id', 'type', 'name', 'members', 'last_message', 'timestamp'])
    return redirect(url_for('chat.room', room_id=room_id))

@chat_bp.route('/room/<room_id>')
@login_required
def room(room_id):
    rooms = CSVManager.read('data/chat_rooms.csv')
    current_room = next((r for r in rooms if r['room_id'] == room_id), None)

    if not current_room:
        return redirect(url_for('chat.index'))

    # Member Check
    my_name = session['user']['name']
    if current_room['type'] != 'global' and my_name not in current_room['members'].split(','):
        flash("이 대화방에 참여할 권한이 없습니다.")
        return redirect(url_for('chat.index'))

    messages = CSVManager.read('data/chat_messages.csv')
    room_messages = [m for m in messages if m['room_id'] == room_id]

    # Format members for display in DM
    display_name = current_room['name']
    if current_room['type'] == 'private':
        members = current_room['members'].split(',')
        other_member = next((m for m in members if m != my_name), my_name)
        display_name = other_member

    return render_template('chat/room.html', room=current_room, messages=room_messages, display_name=display_name)
