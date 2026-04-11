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
        # Permissions check (Security or Military)

        # Mute duration mapping
        durations = {'revolver': 24, 'howitzer': 48, 'sniper': 72, 'icbm': 9999}
        hours = durations.get(weapon, 12)
        expire_at = (datetime.now() + timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')

        new_hit = {
            'target': target,
            'weapon': weapon,
            'attacker': session['user']['name'],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'expire_at': expire_at
        }
        CSVManager.append('data/weapon_hits.csv', new_hit, ['target', 'weapon', 'attacker', 'timestamp', 'expire_at'])
        flash(f"{target}에게 {weapon}(을)를 발사하였습니다!")

    return render_template('more/weapons.html')
