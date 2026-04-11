from flask import Blueprint, render_template, request, session, redirect, url_for, flash, send_file
from utils.csv_manager import CSVManager
from utils.auth import login_required, permission_required
import os

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/')
@login_required
@permission_required('view_csv')
def index():
    users = CSVManager.read('data/users.csv')
    treasury = CSVManager.read('data/treasury.csv')
    complaints = CSVManager.read('data/complaints.csv')
    elections = CSVManager.read('data/elections.csv')

    stats = {
        'user_count': len(users),
        'treasury_balance': treasury[0]['balance'] if treasury else '0',
        'active_trials': len([c for c in complaints if c['status'] == 'trial_ongoing']),
        'active_election': any(e['status'] != 'completed' for e in elections)
    }

    return render_template('admin/index.html', stats=stats)

@admin_bp.route('/csv_editor')
@login_required
@permission_required('edit_csv')
def csv_editor():
    files = [f for f in os.listdir('data') if f.endswith('.csv')]
    return render_template('admin/csv_list.html', files=files)

@admin_bp.route('/csv_editor/<filename>', methods=['GET', 'POST'])
@login_required
@permission_required('edit_csv')
def edit_csv(filename):
    filepath = os.path.join('data', filename)
    if not os.path.exists(filepath):
        flash("파일을 찾을 수 없습니다.")
        return redirect(url_for('admin.csv_editor'))

    data = CSVManager.read(filepath)
    if not data:
        flash("데이터가 없거나 파일이 비어있습니다.")
        return redirect(url_for('admin.csv_editor'))

    headers = list(data[0].keys())

    if request.method == 'POST':
        new_data = []
        # Reconstruct rows from form data
        for i in range(len(data)):
            row = {}
            for h in headers:
                val = request.form.get(f'cell_{i}_{h}')
                row[h] = val
            new_data.append(row)

        CSVManager.write(filepath, new_data, headers)
        flash(f"{filename} 저장 완료")
        return redirect(url_for('admin.edit_csv', filename=filename))
    if data:
        headers = data[0].keys()
    else:
        headers = []

    return render_template('admin/csv_edit.html', filename=filename, data=data, headers=headers)

@admin_bp.route('/users')
@login_required
@permission_required('delete_user')
def manage_users():
    users = CSVManager.read('data/users.csv')
    return render_template('admin/users.html', users=users)

@admin_bp.route('/ban_management')
@login_required
@permission_required('ban_user')
def ban_management():
    users = CSVManager.read('data/users.csv')
    banned_users = [u for u in users if u['status'] == 'banned']
    return render_template('admin/ban_management.html', users=banned_users)

@admin_bp.route('/resolve_ban/<name>/<action>')
@login_required
@permission_required('ban_user')
def resolve_ban(name, action):
    users = CSVManager.read('data/users.csv')
    headers = ['name', 'password', 'birth', 'grade', 'phone', 'resident_id', 'school_info', 'assets', 'status', 'credit_score']

    if action == 'delete':
        users = [u for u in users if u['name'] != name]
        CSVManager.write('data/users.csv', users, headers)
        flash(f"{name} 계정이 영구 삭제되었습니다.")
    elif action == 'restore':
        for u in users:
            if u['name'] == name:
                u['status'] = 'active'
                break
        CSVManager.write('data/users.csv', users, headers)
        # Clear penalties for this user?
        flash(f"{name} 계정이 복구되었습니다.")

    return redirect(url_for('admin.ban_management'))

@admin_bp.route('/approve_user/<name>')
@login_required
@permission_required('set_grade')
def approve_user(name):
    users = CSVManager.read('data/users.csv')
    for u in users:
        if u['name'] == name:
            u['status'] = 'active'
            u['grade'] = '정회원'
            break
    CSVManager.write('data/users.csv', users, ['name', 'password', 'birth', 'grade', 'phone', 'resident_id', 'school_info', 'assets', 'status', 'credit_score'])
    flash(f"{name}님의 가입이 승인되었습니다.")
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/start_election')
@login_required
@permission_required('all')
def start_election():
    from services.election import ElectionService
    ElectionService.start_new_election()
    flash("대통령 선거령이 발령되었습니다.")
    return redirect(url_for('politics.index'))

@admin_bp.route('/emergency', methods=['GET', 'POST'])
@login_required
@permission_required('all')
def emergency():
    if request.method == 'POST':
        em_type = request.form.get('type') # martial_law, emergency, jindogae
        status = request.form.get('status') # active, ended

        records = CSVManager.read('data/emergency_records.csv')
        if status == 'active':
            # End previous active ones
            for r in records: r['status'] = 'ended'
            new_rec = {
                'type': em_type,
                'starter': session['user']['name'],
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'active',
                'end_timestamp': ''
            }
            CSVManager.append('data/emergency_records.csv', new_rec, ['type', 'starter', 'timestamp', 'status', 'end_timestamp'])
            flash(f"{em_type} 선포 완료.")
        else:
            for r in records:
                if r['status'] == 'active':
                    r['status'] = 'ended'
                    r['end_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            CSVManager.write('data/emergency_records.csv', records, ['type', 'starter', 'timestamp', 'status', 'end_timestamp'])
            flash("비상사태가 해제되었습니다.")

    records = CSVManager.read('data/emergency_records.csv')
    return render_template('admin/emergency.html', records=records)

@admin_bp.route('/award', methods=['GET', 'POST'])
@login_required
@permission_required('all')
def award_medal():
    if request.method == 'POST':
        user_name = request.form.get('user')
        medal_name = request.form.get('medal')
        reason = request.form.get('reason')
        reward = int(request.form.get('reward', 0))

        new_medal = {
            'user': user_name,
            'medal_name': medal_name,
            'reason': reason,
            'issuer': session['user']['name'],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'reward': str(reward)
        }
        CSVManager.append('data/medals.csv', new_medal, ['user', 'medal_name', 'reason', 'issuer', 'timestamp', 'reward'])

        if reward > 0:
            from services.economy import EconomyService
            EconomyService.update_user_assets(user_name, reward, f"훈장 수여 포상금 ({medal_name})")

        flash(f"{user_name}님께 {medal_name} 훈장을 수여했습니다.")
        return redirect(url_for('admin.index'))

    return render_template('admin/award.html')
