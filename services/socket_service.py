from flask_socketio import emit, join_room, leave_room
from flask import request, session
from utils.csv_manager import CSVManager
from datetime import datetime
import time

import random
import uuid
from services.economy import EconomyService

# Store last message time for flood protection
last_msg_times = {}

# Multiplayer Dice Battle State
dice_challenges = [] # List of {id, creator, bet, status}

def setup_socket_events(socketio):
    @socketio.on('connect')
    def handle_connect():
        if 'user' in session:
            print(f"User connected: {session['user']['name']}")

    @socketio.on('join')
    def on_join(data):
        room = data['room']
        join_room(room)

    @socketio.on('send_message')
    def handle_message(data):
        if 'user' not in session: return

        user_name = session['user']['name']
        room_id = data['room']
        msg = data['msg']

        # 0. Emergency/Martial Law Logic
        emergencies = CSVManager.read('data/emergency_records.csv')
        active_em = next((e for e in emergencies if e['status'] == 'active'), None)

        if active_em:
            em_type = active_em['type']
            # Jindogae 1, 2, 3 or Martial Law
            if em_type in ['진도개 하나', '진도개 둘', '진도개 셋', '계엄령']:
                # Emoji detection (simplified: check for common emoji ranges or [em] tags)
                # For this implementation, we assume if the message contains non-BMP characters or common symbols
                if any(ord(c) > 0xFFFF for c in msg):
                    emit('error', {'msg': f'{em_type} 발령 중에는 이모티콘 사용이 금지됩니다.'})
                    return

            if em_type == '진도개 셋':
                # Minimize chat (e.g., max length)
                if len(msg) > 50:
                    emit('error', {'msg': '진도개 셋 발령 중에는 필요한 공적 발언(50자 이내)만 허용됩니다.'})
                    return

            if em_type == '계엄령':
                # Suspension of private talk?
                # The rule says "No chatter/private chat"
                pass

        # 1. Flood Protection
        now = time.time()
        n = int(CSVManager.get_config('spam_n') or 5)
        m = int(CSVManager.get_config('spam_m') or 3)

        user_history = last_msg_times.get(user_name, [])
        user_history = [t for t in user_history if now - t < n]
        if len(user_history) >= m:
            emit('error', {'msg': '도배 방지: 잠시 후 다시 시도해주세요.'})
            return

        user_history.append(now)
        last_msg_times[user_name] = user_history

        # 2. Swear Filter
        filter_words = CSVManager.read('data/filter_words.csv')
        for f in filter_words:
            if f['word'] in msg:
                emit('error', {'msg': '욕설이 감지되었습니다. 경고가 누적됩니다.'})
                return

        # 3. Save to CSV
        log_msg = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'room_id': room_id,
            'sender': user_name,
            'message': msg
        }
        CSVManager.append('data/chat_messages.csv', log_msg, ['timestamp', 'room_id', 'sender', 'message'])

        # 4. Broadcast
        emit('receive_message', {
            'sender': user_name,
            'msg': msg,
            'timestamp': log_msg['timestamp'],
            'grade': session['user']['grade']
        }, room=room_id)

    @socketio.on('leave')
    def on_leave(data):
        room = data['room']
        leave_room(room)

    # Multiplayer Dice Battle Events
    @socketio.on('dice_create_challenge')
    def handle_create_dice(data):
        if 'user' not in session: return
        user_name = session['user']['name']
        bet = int(data.get('bet', 10000))

        # Check assets
        if EconomyService.get_user_assets(user_name) < bet:
            emit('error', {'msg': '잔액이 부족합니다.'})
            return

        challenge_id = str(uuid.uuid4())
        new_challenge = {
            'id': challenge_id,
            'creator': user_name,
            'bet': bet,
            'status': 'waiting'
        }
        dice_challenges.append(new_challenge)
        emit('dice_lobby_update', dice_challenges, broadcast=True)

    @socketio.on('dice_join_challenge')
    def handle_join_dice(data):
        if 'user' not in session: return
        user_name = session['user']['name']
        c_id = data.get('challenge_id')

        challenge = next((c for c in dice_challenges if c['id'] == c_id and c['status'] == 'waiting'), None)
        if not challenge: return
        if challenge['creator'] == user_name: return # Can't play vs self

        # Check assets
        if EconomyService.get_user_assets(user_name) < challenge['bet']:
            emit('error', {'msg': '잔액이 부족합니다.'})
            return

        challenge['status'] = 'ongoing'
        challenge['opponent'] = user_name

        room_id = f"dice_{c_id}"
        join_room(room_id)

        emit('dice_battle_start', {
            'room': room_id,
            'p1': challenge['creator'],
            'p2': challenge['opponent'],
            'bet': challenge['bet']
        }, broadcast=True) # Or just emit to participants

        # Simulate Battle
        time.sleep(2)
        p1_roll = random.randint(1, 6)
        p2_roll = random.randint(1, 6)

        winner = 'draw'
        if p1_roll > p2_roll:
            winner = challenge['creator']
            EconomyService.update_user_assets(challenge['creator'], challenge['bet'], "주사위 배틀 승리")
            EconomyService.update_user_assets(challenge['opponent'], -challenge['bet'], "주사위 배틀 패배")
        elif p2_roll > p1_roll:
            winner = challenge['opponent']
            EconomyService.update_user_assets(challenge['opponent'], challenge['bet'], "주사위 배틀 승리")
            EconomyService.update_user_assets(challenge['creator'], -challenge['bet'], "주사위 배틀 패배")
        else:
            # Draw: No change
            pass

        emit('dice_battle_result', {
            'p1_roll': p1_roll,
            'p2_roll': p2_roll,
            'winner': winner
        }, room=room_id)

        # Cleanup
        challenge['status'] = 'finished'
        emit('dice_lobby_update', dice_challenges, broadcast=True)
