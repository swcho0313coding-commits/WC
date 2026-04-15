from flask import Blueprint, render_template, request, session, redirect, url_for, flash, send_file
from utils.csv_manager import CSVManager
from utils.auth import login_required, permission_required
from services.economy import EconomyService
from datetime import datetime
import os

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/')
@login_required
@permission_required('view_csv')
def index():
    users = CSVManager.read('data/users.csv')
    treasury_data = CSVManager.read('data/treasury.csv')
    complaints = CSVManager.read('data/complaints.csv')
    elections = CSVManager.read('data/elections.csv')

    # Placeholder Replacement for Grades in Admin View
    country = CSVManager.get_config('country_name')
    for u in users:
        u['grade'] = u['grade'].replace('{국가이름}', country)

    stats = {
        'user_count': len(users),
        'treasury_balance': treasury_data[-1]['balance'] if treasury_data else '0',
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

@admin_bp.route('/law_editor')
@login_required
@permission_required('edit_csv')
def law_editor():
    files = [f for f in os.listdir('data/laws') if f.endswith('.txt')]
    return render_template('admin/law_list.html', files=files)

@admin_bp.route('/law_editor/<filename>', methods=['GET', 'POST'])
@login_required
@permission_required('edit_csv')
def edit_law(filename):
    filepath = os.path.join('data/laws', filename)
    if request.method == 'POST':
        content = request.form.get('content')
        with open(filepath, 'w', encoding='utf-8-sig') as f:
            f.write(content)
        flash(f"{filename} 법안 수정 완료")
        return redirect(url_for('admin.law_editor'))

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    return render_template('admin/law_edit.html', filename=filename, content=content)

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
        # If file empty, we can't easily edit without headers.
        # But our system ensures files have headers.
        flash("데이터가 없거나 파일이 비어있습니다.")
        return redirect(url_for('admin.csv_editor'))

    headers = list(data[0].keys())

    if request.method == 'POST':
        new_data = []
        # Reconstruct rows from form data
        # Note: This is a simple editor. For production, more robust handling needed.
        for i in range(len(data)):
            row = {}
            for h in headers:
                val = request.form.get(f'cell_{i}_{h}')
                row[h] = val
            new_data.append(row)

        CSVManager.write(filepath, new_data, headers)
        flash(f"{filename} 저장 완료")
        return redirect(url_for('admin.edit_csv', filename=filename))

    return render_template('admin/csv_edit.html', filename=filename, data=data, headers=headers)

@admin_bp.route('/users')
@login_required
@permission_required('delete_user')
def manage_users():
    users = CSVManager.read('data/users.csv')
    return render_template('admin/users.html', users=users)

@admin_bp.route('/approve_user/<name>')
@login_required
@permission_required('set_grade')
def approve_user(name):
    users = CSVManager.read('data/users.csv')
    found = False
    for u in users:
        if u['name'] == name:
            u['status'] = 'active'
            u['grade'] = '국민 9등급' # Standard starting citizen grade
            found = True
            break

    if found:
        CSVManager.write('data/users.csv', users, ['name', 'login_id', 'password', 'birth', 'grade', 'phone', 'resident_id', 'school_info', 'assets', 'status', 'credit_score', 'last_update_year'])

        # Grant 50,000 starting bonus
        bonus = int(CSVManager.get_config('initial_assets') or 50000)
        EconomyService.update_user_assets(name, bonus, "정회원 승인 초기 자산 지급")

        flash(f"{name}님의 가입이 승인되었으며, {bonus} {CSVManager.get_config('currency_name')}이 지급되었습니다.")
        CSVManager.log_activity(request.remote_addr, session['user']['name'], f"Approved user {name}", "success")
    else:
        flash("사용자를 찾을 수 없습니다.")

    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/force_grade_update')
@login_required
@permission_required('all')
def force_grade_update():
    # Set a flag in config to force all users to update their info
    configs = CSVManager.read('data/config.csv')
    found = False
    for c in configs:
        if c['key'] == 'force_info_update':
            c['value'] = 'true'
            found = True
    if not found:
        configs.append({'key': 'force_info_update', 'value': 'true'})

    CSVManager.write('data/config.csv', configs, ['key', 'value'])
    flash("모든 사용자에게 학년/반 정보 업데이트가 강제되었습니다.")
    return redirect(url_for('admin.index'))

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
        em_type = request.form.get('type')
        status = request.form.get('status')

        records = CSVManager.read('data/emergency_records.csv')
        if status == 'active':
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

@admin_bp.route('/logs')
@login_required
@permission_required('view_logs')
def view_logs():
    logs = CSVManager.read('data/logs/activity.csv')
    return render_template('admin/logs.html', logs=logs[::-1]) # Reverse to show newest

@admin_bp.route('/ip_blocks', methods=['GET', 'POST'])
@login_required
@permission_required('all')
def manage_ip_blocks():
    if request.method == 'POST':
        ip = request.form.get('ip')
        reason = request.form.get('reason')
        CSVManager.append('data/ip_blocks.csv', {'ip': ip, 'reason': reason}, ['ip', 'reason'])
        flash(f"IP {ip} 차단 완료")

    blocks = CSVManager.read('data/ip_blocks.csv')
    return render_template('admin/ip_blocks.html', blocks=blocks)

@admin_bp.route('/unblock_ip/<ip>')
@login_required
@permission_required('all')
def unblock_ip(ip):
    blocks = CSVManager.read('data/ip_blocks.csv')
    new_blocks = [b for b in blocks if b['ip'] != ip]
    CSVManager.write('data/ip_blocks.csv', new_blocks, ['ip', 'reason'])
    flash(f"IP {ip} 차단 해제")
    return redirect(url_for('admin.manage_ip_blocks'))

@admin_bp.route('/pay_salaries_manual')
@login_required
@permission_required('all')
def pay_salaries_manual():
    EconomyService.pay_salaries()
    flash("주급 지급이 수동으로 완료되었습니다.")
    return redirect(url_for('admin.index'))

@admin_bp.route('/treasury_manage', methods=['GET', 'POST'])
@login_required
@permission_required('all')
def treasury_manage():
    if request.method == 'POST':
        amount = int(request.form.get('amount', 0))
        reason = request.form.get('reason', '관리자 직접 집행')
        EconomyService.update_treasury(amount, reason)
        flash(f"국고 {'입금' if amount > 0 else '출금'} {abs(amount)} 완료")

    treasury = CSVManager.read('data/treasury.csv')
    balance = treasury[-1]['balance'] if treasury else '0'
    return render_template('admin/treasury.html', balance=balance)

@admin_bp.route('/ban_management')
@login_required
@permission_required('all')
def ban_management():
    # Show users with status 'banned' or penalties >= 200
    users = CSVManager.read('data/users.csv')
    banned_users = [u for u in users if u['status'] == 'banned']
    return render_template('admin/ban_management.html', users=banned_users)

@admin_bp.route('/resolve_ban/<name>/<action>')
@login_required
@permission_required('all')
def resolve_ban(name, action):
    users = CSVManager.read('data/users.csv')
    for u in users:
        if u['name'] == name:
            if action == 'delete' or action == 'approve':
                u['status'] = 'deleted'
                # Optionally block IP
                flash(f"{name} 계정 삭제 및 영구 처분이 완료되었습니다.")
            else:
                u['status'] = 'active'
                # Reset penalties
                penalties = CSVManager.read('data/penalties.csv')
                new_penalties = [p for p in penalties if p['user'] != name]
                CSVManager.write('data/penalties.csv', new_penalties, ['user', 'reason', 'score', 'issuer', 'timestamp'])
                flash(f"{name} 계정 복구 및 벌점 초기화가 완료되었습니다.")
            break
    CSVManager.write('data/users.csv', users, ['name', 'login_id', 'password', 'birth', 'grade', 'phone', 'resident_id', 'school_info', 'assets', 'status', 'credit_score'])
    return redirect(url_for('admin.ban_management'))

@admin_bp.route('/award', methods=['GET', 'POST'])
@login_required
@permission_required('all')
def award_medal():
    if request.method == 'POST':
        user_name = request.form.get('user')
        user_phone = request.form.get('phone')
        medal_name = request.form.get('medal')
        reason = request.form.get('reason')
        reward = int(request.form.get('reward', 0))

        # Verify Identity
        users = CSVManager.read('data/users.csv')
        recipient = next((u for u in users if u['name'] == user_name and u['phone'] == user_phone), None)
        if not recipient:
            flash("사용자 정보(이름/전화번호)가 일치하지 않습니다.")
            return redirect(url_for('admin.award_medal'))

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
            EconomyService.update_user_assets(user_name, reward, f"훈장 수여 포상금 ({medal_name})")

        flash(f"{user_name}님께 {medal_name} 훈장을 수여했습니다.")
        return redirect(url_for('admin.index'))

    return render_template('admin/award.html')
