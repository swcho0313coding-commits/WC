from flask import Flask, render_template, session, request, redirect, url_for, flash
from flask_socketio import SocketIO
from apscheduler.schedulers.background import BackgroundScheduler
import os
from datetime import datetime
from utils.csv_manager import CSVManager
from routes.auth import auth_bp
from routes.sns import sns_bp
from routes.chat import chat_bp
from routes.politics import politics_bp
from routes.legal import legal_bp
from routes.games import games_bp
from routes.admin import admin_bp
from routes.bank import bank_bp
from routes.more import more_bp
from routes.mypage import mypage_bp
from services.economy import EconomyService
from services.election import ElectionService
from services.socket_service import setup_socket_events

app = Flask(__name__)
app.secret_key = 'virtual-state-secret-key'
socketio = SocketIO(app)

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(sns_bp, url_prefix='/sns')
app.register_blueprint(chat_bp, url_prefix='/chat')
app.register_blueprint(politics_bp, url_prefix='/politics')
app.register_blueprint(legal_bp, url_prefix='/legal')
app.register_blueprint(games_bp, url_prefix='/games')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(bank_bp, url_prefix='/bank')
app.register_blueprint(more_bp, url_prefix='/more')
app.register_blueprint(mypage_bp, url_prefix='/mypage')

# SocketIO Setup
setup_socket_events(socketio)

# Scheduler Setup
scheduler = BackgroundScheduler()
scheduler.add_job(func=EconomyService.pay_salaries, trigger="interval", weeks=1)
scheduler.add_job(func=ElectionService.transition_phases, trigger="interval", hours=1)

def check_grade_update_needed(user):
    now = datetime.now()
    force_update = CSVManager.get_config('force_info_update') == 'true'
    is_march_1st_or_later = (now.month >= 3 or (now.month == 3 and now.day >= 1))

    val = user.get('last_update_year')
    user_last_year = int(val) if val and str(val).isdigit() else 0

    # If it's a new year's March 1st and USER hasn't updated for this year yet
    if (now.year > user_last_year and is_march_1st_or_later) or force_update:
        return True
    return False

@app.before_request
def check_requirements():
    if request.path.startswith('/static') or request.path.startswith('/auth'):
        return

    ip = request.remote_addr
    blocks = CSVManager.read('data/ip_blocks.csv')
    for b in blocks:
        if b['ip'] == ip:
            return f"접속이 차단되었습니다. 사유: {b['reason']}", 403

    if 'user' in session:
        # 3월 1일 이후 첫 로그인 시 정보 수정 강제
        if check_grade_update_needed(session['user']):
            if not request.path.startswith('/mypage/update_info'):
                flash("3월 1일 새 학기를 맞아 학년/반 정보를 갱신해야 합니다.")
                return redirect(url_for('mypage.update_info'))

# Context Processor
@app.context_processor
def inject_config():
    country = CSVManager.get_config('country_name')
    currency = CSVManager.get_config('currency_name')
    motto = CSVManager.get_config('national_motto')
    anthem = CSVManager.get_config('national_anthem_url')
    return {
        'config_country_name': country,
        'config_currency_name': currency,
        'config_national_motto': motto,
        'config_national_anthem': anthem
    }

def replace_placeholders(text):
    if not text: return text
    country = CSVManager.get_config('country_name')
    currency = CSVManager.get_config('currency_name')
    return text.replace('{국가이름}', country).replace('{화폐단위}', currency)

app.jinja_env.filters['replace_placeholders'] = replace_placeholders

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    country = CSVManager.get_config('country_name')
    users = CSVManager.read('data/users.csv')
    for u in users:
        u['grade'] = u['grade'].replace('{국가이름}', country)
    user = next((u for u in users if u['login_id'] == session['user']['login_id']), None)
    if not user:
        session.pop('user', None)
        return redirect(url_for('auth.login'))

    session['user'] = user
    return render_template('index.html', user=user)

@app.route('/survival', methods=['POST'])
def survival():
    if 'user' not in session: return redirect(url_for('auth.login'))
    user_name = session['user']['name']
    date = datetime.now().strftime('%Y-%m-%d')

    recs = CSVManager.read('data/attendance.csv')
    if any(r['user'] == user_name and r['date'] == date for r in recs):
        flash("이미 오늘의 생존신고를 완료했습니다.")
    else:
        CSVManager.append('data/attendance.csv',
                          {'user': user_name, 'date': date, 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
                          ['user', 'date', 'timestamp'])
        flash("생존신고가 완료되었습니다.")
    return redirect(url_for('index'))

if __name__ == '__main__':
    scheduler.start()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
