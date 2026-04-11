from flask_socketio import emit, join_room, leave_room
from flask import session, request
from utils.csv_manager import CSVManager
from datetime import datetime

def setup_socket_events(socketio):
    @socketio.on('join')
    def on_join(data):
        room = data['room']
        join_room(room)
        # emit('status', {'msg': f"{session['user']['name']}님이 입장하셨습니다."}, room=room)

    @socketio.on('message')
    def handle_message(data):
        # Flood protection
        now = datetime.now()
        last_time = session.get('last_msg_time')
        msg_count = session.get('msg_count', 0)

        if last_time:
            last_dt = datetime.fromisoformat(last_time)
            if (now - last_dt).total_seconds() < 2: # N=2 seconds
                msg_count += 1
                if msg_count > 3: # M=3 messages
                    emit('error', {'msg': '도배 금지! 잠시 후 다시 시도하세요.'}, room=request.sid)
                    return
            else:
                msg_count = 1
        else:
            msg_count = 1

        session['last_msg_time'] = now.isoformat()
        session['msg_count'] = msg_count

        room = data['room']
        content = data['message']
        sender = session['user']['name']
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Filter check
        filters = CSVManager.read('data/filter_words.csv')
        for f in filters:
            if f['word'] in content:
                emit('error', {'msg': '부적절한 표현이 포함되어 있습니다.'}, room=request.sid)
                return

        new_msg = {
            'room_id': room,
            'sender': sender,
            'content': content,
            'timestamp': timestamp
        }
        CSVManager.append('data/chat_messages.csv', new_msg, ['room_id', 'sender', 'content', 'timestamp'])

        emit('message', new_msg, room=room)

        # Update last message in room
        rooms = CSVManager.read('data/chat_rooms.csv')
        for r in rooms:
            if r['room_id'] == room:
                r['last_message'] = content
                r['timestamp'] = timestamp
                break
        CSVManager.write('data/chat_rooms.csv', rooms, ['room_id', 'type', 'name', 'members', 'last_message', 'timestamp'])
