from flask import Flask, render_template, session, request
from flask_socketio import SocketIO
from apscheduler.schedulers.background import BackgroundScheduler
import os
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
app.secret_key = 'super-secret-key' # In real world, use env var
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
scheduler.add_job(func=EconomyService.pay_salaries, trigger="interval", weeks=1) # Weekly salaries
scheduler.add_job(func=ElectionService.transition_phases, trigger="interval", hours=1)
scheduler.start()

# IP Blocking Check
@app.before_request
def check_ip_block():
    ip = request.remote_addr
    blocks = CSVManager.read('data/ip_blocks.csv')
    for b in blocks:
        if b['ip'] == ip:
            return f"Access Denied: Your IP ({ip}) is blocked. Reason: {b['reason']}", 403

# Context Processor for common variables
@app.context_processor
def inject_config():
    return {
        'config_country_name': CSVManager.get_config('country_name'),
        'config_currency_name': CSVManager.get_config('currency_name')
    }

@app.route('/')
def index():
    if 'user' not in session:
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))

    # Refresh user session from CSV to catch grade changes
    from utils.auth import get_user_by_name
    user = get_user_by_name(session['user']['name'])
    session['user'] = user

    return render_template('index.html', user=user)

@app.route('/survival', methods=['POST'])
def survival():
    if 'user' not in session: return redirect(url_for('auth.login'))
    user = session['user']['name']
    date = datetime.now().strftime('%Y-%m-%d')

    # Check if already done today
    recs = CSVManager.read('data/attendance.csv')
    if any(r['user'] == user and r['date'] == date for r in recs):
        flash("이미 생존신고를 완료했습니다.")
    else:
        CSVManager.append('data/attendance.csv',
                          {'user': user, 'date': date, 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
                          ['user', 'date', 'timestamp'])
        flash("생존신고가 완료되었습니다.")
    return redirect(url_for('index'))

# Placeholder routes for navigation (will be replaced by actual blueprints)



if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)
