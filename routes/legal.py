from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from utils.csv_manager import CSVManager
from utils.auth import login_required, permission_required
from datetime import datetime
import uuid
from services.economy import EconomyService

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
    user_grade = session['user']['grade']
    if user_grade not in ['사법 1등급', '보안 0등급', '관리자']:
        flash("권한이 없습니다.")
        return redirect(url_for('legal.cases'))

    cases = CSVManager.read('data/complaints.csv')
    for c in cases:
        if c['id'] == case_id:
            c['status'] = 'trial_ongoing'
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
@permission_required('all')
def verdict(case_id):
    tier = request.form.get('tier', '1')
    result = request.form.get('result')
    fine = int(request.form.get('fine', 0))
    penalty_score = int(request.form.get('penalty_score', 0))

    cases = CSVManager.read('data/complaints.csv')
    case = next((c for c in cases if c['id'] == case_id), None)
    if not case: return redirect(url_for('legal.cases'))

    if tier == '1': case['status'] = f'tier1_{result}'
    elif tier == '2': case['status'] = f'tier2_{result}'
    elif tier == '3': case['status'] = f'final_{result}'

    if result == 'guilty' and tier == '3':
        EconomyService.update_user_assets(case['target'], -fine, f"재판 최종 판결 벌금 ({case_id})")
        CSVManager.add_penalty(case['target'], f"재판 최종 판결 ({case_id})", penalty_score, session['user']['name'])

    CSVManager.write('data/complaints.csv', cases, ['id', 'reporter', 'target', 'reason', 'law_id', 'status', 'timestamp'])
    flash(f"{tier}심 판결이 등록되었습니다.")
    return redirect(url_for('legal.view_case', case_id=case_id))

@legal_bp.route('/statutes')
@login_required
def list_statutes():
    # Dynamic reading from laws folder
    files = [f for f in os.listdir('data/laws') if f.endswith('.txt') or f.endswith('.md')]
    return render_template('legal/statutes.html', files=files)

@legal_bp.route('/statutes/<name>')
@login_required
def view_statute(name):
    filepath = os.path.join('data/laws', name)
    if not os.path.exists(filepath): return redirect(url_for('legal.list_statutes'))

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    # Placeholder Replacement
    country = CSVManager.get_config('country_name')
    currency = CSVManager.get_config('currency_name')
    content = content.replace('{국가이름}', country).replace('{화폐단위}', currency)

    return render_template('legal/view_statute.html', name=name, content=content)
