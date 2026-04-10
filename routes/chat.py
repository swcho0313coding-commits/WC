from flask import Blueprint, render_template, request, session, redirect, url_for
from utils.csv_manager import CSVManager
from utils.auth import login_required

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/')
@login_required
def index():
    rooms = CSVManager.read('data/chat_rooms.csv')
    username = session['user']['name']

    user_rooms = []
    for r in rooms:
        if r['type'] == 'global' or username in r['members'].split(','):
            user_rooms.append(r)

    return render_template('chat/index.html', rooms=user_rooms)

@chat_bp.route('/room/<room_id>')
@login_required
def room(room_id):
    rooms = CSVManager.read('data/chat_rooms.csv')
    current_room = next((r for r in rooms if r['room_id'] == room_id), None)

    if not current_room:
        return redirect(url_for('chat.index'))

    messages = CSVManager.read('data/chat_messages.csv')
    room_messages = [m for m in messages if m['room_id'] == room_id]

    return render_template('chat/room.html', room=current_room, messages=room_messages)
