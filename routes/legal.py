from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from utils.csv_manager import CSVManager
from utils.auth import login_required, permission_required
from datetime import datetime
import uuid

legal_bp = Blueprint('legal', __name__)

@legal_bp.route('/')
@login_required
def index():
    laws = CSVManager.read('data/laws.csv')
    return render_template('legal/index.html', laws=laws)

@legal_bp.route('/report', methods=['GET', 'POST'])
@login_required
def report():
    if request.method == 'POST':
        target = request.form.get('target')
        reason = request.form.get('reason')
        law_id = request.form.get('law_id')

        new_complaint = {
            'id': str(uuid.uuid4()),
            'reporter': session['user']['name'],
            'target': target,
            'reason': reason,
            'law_id': law_id,
            'status': 'pending',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        CSVManager.append('data/complaints.csv', new_complaint,
                          ['id', 'reporter', 'target', 'reason', 'law_id', 'status', 'timestamp'])

        flash("고발이 접수되었습니다. 사법부 검토 후 재판이 진행됩니다.")
        return redirect(url_for('legal.index'))

    users = CSVManager.read('data/users.csv')
    laws = CSVManager.read('data/laws.csv')
    return render_template('legal/report.html', users=users, laws=laws)

@legal_bp.route('/cases')
@login_required
def cases():
    cases = CSVManager.read('data/complaints.csv')
    return render_template('legal/cases.html', cases=cases)

@legal_bp.route('/case/<case_id>')
@login_required
def view_case(case_id):
    cases = CSVManager.read('data/complaints.csv')
    case = next((c for c in cases if c['id'] == case_id), None)
    if not case: return redirect(url_for('legal.cases'))

    laws = CSVManager.read('data/laws.csv')
    law = next((l for l in laws if l['id'] == case['law_id']), None)

    return render_template('legal/view_case.html', case=case, law=law)

@legal_bp.route('/approve/<case_id>')
@login_required
def approve_case(case_id):
    # Only 사법 1등급 or 보안 0등급 or 관리자 can approve
    user_grade = session['user']['grade']
    if user_grade not in ['사법 1등급', '보안 0등급', '관리자']:
        flash("권한이 없습니다.")
        return redirect(url_for('legal.cases'))

    cases = CSVManager.read('data/complaints.csv')
    for c in cases:
        if c['id'] == case_id:
            c['status'] = 'trial_ongoing'
            # Create a special chat room for trial
            new_room = {
                'room_id': f"trial_{case_id}",
                'type': 'private',
                'name': f"재판: {c['target']} 사건",
                'members': f"{c['reporter']},{c['target']},관리자",
                'last_message': '재판이 개시되었습니다.',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            CSVManager.append('data/chat_rooms.csv', new_room, ['room_id', 'type', 'name', 'members', 'last_message', 'timestamp'])
            break
    CSVManager.write('data/complaints.csv', cases, ['id', 'reporter', 'target', 'reason', 'law_id', 'status', 'timestamp'])
    flash("사건이 승인되었습니다. 재판 채팅방이 생성되었습니다.")
    return redirect(url_for('legal.cases'))

@legal_bp.route('/verdict/<case_id>', methods=['POST'])
@login_required
@permission_required('all') # Admin or 사법 1등급 (simplified)
def verdict(case_id):
    result = request.form.get('result') # guilty, innocent
    fine = int(request.form.get('fine', 0))

    cases = CSVManager.read('data/complaints.csv')
    case = next((c for c in cases if c['id'] == case_id), None)
    if not case: return redirect(url_for('legal.cases'))

    if result == 'guilty':
        case['status'] = 'guilty'
        if fine > 0:
            EconomyService.update_user_assets(case['target'], -fine, f"재판 판결 벌금 납부 ({case_id})")
            EconomyService.update_treasury(fine, f"재판 벌금 수입 ({case_id})")
    else:
        case['status'] = 'innocent'

    CSVManager.write('data/complaints.csv', cases, ['id', 'reporter', 'target', 'reason', 'law_id', 'status', 'timestamp'])

    # Record in criminal records
    record = {
        'user': case['target'],
        'crime': case['reason'],
        'punishment': f"{result} (벌금 {fine})" if result == 'guilty' else 'innocent',
        'date': datetime.now().strftime('%Y-%m-%d')
    }
    CSVManager.append('data/criminal_records.csv', record, ['user', 'crime', 'punishment', 'date'])

    flash("판결이 확정 및 집행되었습니다.")
    return redirect(url_for('legal.cases'))
