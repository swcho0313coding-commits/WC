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
        # Mute check (Weapon hits)
        username = session['user']['name']
        hits = CSVManager.read('data/weapon_hits.csv')
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for h in hits:
            if h['target'] == username and h['expire_at'] > now_str:
                emit('error', {'msg': f"당신은 무기에 피격되어 대화가 금지되었습니다. (만료: {h['expire_at']})"}, room=request.sid)
                return

        # Martial Law / Emergency Check
        from services.emergency import EmergencyService
        is_em, em_type = EmergencyService.is_emergency()
        if is_em and em_type == 'martial_law':
            # Check for잡담 (simplified: messages without "!")
            if "!" not in content and "?" not in content:
                 # In martial law, only essential 공적 발언 (simplified check)
                 pass

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

    @socketio.on('file_upload')
    def handle_file(data):
        # In a real app, we'd handle the binary data.
        # Here we simplified: just notify and log.
        room = data['room']
        sender = session['user']['name']
        filename = data['filename']

        new_msg = {
            'room_id': room,
            'sender': sender,
            'content': f"[파일 전송됨: {filename}]",
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
