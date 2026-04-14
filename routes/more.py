from flask import Blueprint, render_template, session, request, flash
from utils.auth import login_required
from utils.csv_manager import CSVManager
from datetime import datetime, timedelta

more_bp = Blueprint('more', __name__)

@more_bp.route('/')
@login_required
def index():
    return render_template('more/index.html')

@more_bp.route('/qr_scan')
@login_required
def qr_scan():
    return render_template('more/qr_scan.html')

@more_bp.route('/weapons', methods=['GET', 'POST'])
@login_required
def weapons():
    if request.method == 'POST':
        target = request.form.get('target')
        weapon = request.form.get('weapon')

        # Load weapon config
        configs = CSVManager.read('data/weapons_config.csv')
        w_conf = next((c for c in configs if c['weapon'] == weapon), {'mute_hours': '12', 'death_hits': '0'})

        hours = int(w_conf['mute_hours'])
        death_limit = int(w_conf['death_hits'])

        expire_at = (datetime.now() + timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')

        new_hit = {
            'target': target,
            'weapon': weapon,
            'attacker': session['user']['name'],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'expire_at': expire_at
        }
        CSVManager.append('data/weapon_hits.csv', new_hit, ['target', 'weapon', 'attacker', 'timestamp', 'expire_at'])

        # Check death (force exit) logic
        hits = CSVManager.read('data/weapon_hits.csv')
        # Filter for recent hits (within a week as per Military Act Art 46)
        one_week_ago = datetime.now() - timedelta(days=7)
        user_hits = [h for h in hits if h['target'] == target and h['weapon'] == weapon and datetime.strptime(h['timestamp'], '%Y-%m-%d %H:%M:%S') > one_week_ago]

        if death_limit > 0 and len(user_hits) >= death_limit:
            # Kill user (status -> deleted)
            users = CSVManager.read('data/users.csv')
            for u in users:
                if u['name'] == target:
                    u['status'] = 'deleted'
                    flash(f"{target}님이 {weapon}에 의해 전사(강제퇴장)하셨습니다.")
                    break
            CSVManager.write('data/users.csv', users, ['name', 'login_id', 'password', 'birth', 'grade', 'phone', 'resident_id', 'school_info', 'assets', 'status', 'credit_score', 'last_update_year'])
        else:
            flash(f"{target}에게 {weapon}(을)를 발사하였습니다! ({hours}시간 발언 금지)")

    return render_template('more/weapons.html')
