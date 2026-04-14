from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from utils.csv_manager import CSVManager
from utils.auth import login_required, permission_required
from datetime import datetime
import uuid
from services.economy import EconomyService
import os

legal_bp = Blueprint('legal', __name__)

@legal_bp.route('/')
@login_required
def index():
    return render_template('legal/index.html')

@legal_bp.route('/statutes')
@login_required
def list_statutes():
    # Show active statutes
    laws_list = [f for f in os.listdir('data/laws') if f.endswith('.txt') or f.endswith('.md')]
    return render_template('legal/statutes.html', files=laws_list)

@legal_bp.route('/statutes/<name>')
@login_required
def view_statute(name):
    filepath = os.path.join('data/laws', name)
    if not os.path.exists(filepath): return redirect(url_for('legal.index'))

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    # Placeholder Replacement
    country = CSVManager.get_config('country_name')
    currency = CSVManager.get_config('currency_name')
    content = content.replace('{국가이름}', country).replace('{화폐단위}', currency)

    # Also apply the jinja filter manually if needed or just trust the render_template
    # Actually the content passed to render_template will be used as is.
    return render_template('legal/view_statute.html', name=name, content=content)

@legal_bp.route('/cases')
@login_required
def cases():
    complaints = CSVManager.read('data/complaints.csv')
    return render_template('legal/cases.html', cases=complaints)

@legal_bp.route('/report', methods=['GET', 'POST'])
@login_required
def report():
    if request.method == 'POST':
        target = request.form.get('target')
        reason = request.form.get('reason')
        law_title = request.form.get('law_title')

        new_complaint = {
            'id': str(uuid.uuid4()),
            'reporter': session['user']['name'],
            'target': target,
            'reason': reason,
            'law_title': law_title,
            'status': 'pending',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        CSVManager.append('data/complaints.csv', new_complaint,
                          ['id', 'reporter', 'target', 'reason', 'law_title', 'status', 'timestamp'])

        flash("고발이 접수되었습니다. 사법부 검토 후 재판이 진행됩니다.")
        return redirect(url_for('legal.cases'))

    users = CSVManager.read('data/users.csv')
    return render_template('legal/report.html', users=users)

@legal_bp.route('/case/<case_id>')
@login_required
def view_case(case_id):
    complaints = CSVManager.read('data/complaints.csv')
    case = next((c for c in complaints if c['id'] == case_id), None)
    if not case: return redirect(url_for('legal.cases'))

    # Placeholder Replacement for Law Content in View
    country = CSVManager.get_config('country_name')
    currency = CSVManager.get_config('currency_name')

    # Try to find the law content if applicable
    law_content = ""
    law_file = f"data/laws/{case['law_title']}.txt"
    if os.path.exists(law_file):
        with open(law_file, 'r', encoding='utf-8-sig') as f:
            law_content = f.read().replace('{국가이름}', country).replace('{화폐단위}', currency)

    return render_template('legal/view_case.html', case=case, law_content=law_content)

@legal_bp.route('/approve/<case_id>')
@login_required
def approve_case(case_id):
    user_grade = session['user']['grade']
    # 1st tier approval: 사법 1등급 or Admin
    if user_grade not in ['사법 1등급', '관리자']:
        flash("사법 1등급만 사건을 1차 승인할 수 있습니다.")
        return redirect(url_for('legal.cases'))

    complaints = CSVManager.read('data/complaints.csv')
    for c in complaints:
        if c['id'] == case_id:
            c['status'] = 'trial_ongoing'
            # Create trial chat room
            new_room = {
                'room_id': f"trial_{case_id}",
                'type': 'private',
                'name': f"재판: {c['target']} 피고인",
                'members': f"{c['reporter']},{c['target']},관리자,사법 1등급",
                'last_message': '사건 1차 승인 완료. 재판이 개시되었습니다.',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            CSVManager.append('data/chat_rooms.csv', new_room, ['room_id', 'type', 'name', 'members', 'last_message', 'timestamp'])
            break
    CSVManager.write('data/complaints.csv', complaints, ['id', 'reporter', 'target', 'reason', 'law_title', 'status', 'timestamp'])
    flash("사건이 1차 승인되었습니다. 재판 채팅방이 생성되었습니다.")
    return redirect(url_for('legal.cases'))

@legal_bp.route('/verdict/<case_id>', methods=['POST'])
@login_required
def verdict(case_id):
    # Tier 1 verdict: Supreme Court Chief (관리자 or 대법원장)
    # Tier 2: AI (Managed by Admin)
    # Tier 3: High Council (Admin, Vice-Admin, Security Chief, President)

    tier = request.form.get('tier')
    result = request.form.get('result') # guilty, innocent, retrial
    fine = int(request.form.get('fine', 0))
    penalty_score = int(request.form.get('penalty_score', 0))

    complaints = CSVManager.read('data/complaints.csv')
    case = next((c for c in complaints if c['id'] == case_id), None)
    if not case: return redirect(url_for('legal.cases'))

    # Permissions check for each tier
    user_grade = session['user']['grade']
    if tier == '1':
        if user_grade not in ['관리자', '대법원장']:
            flash("1심은 대법원장만이 판결할 수 있습니다.")
            return redirect(url_for('legal.view_case', case_id=case_id))
    elif tier == '3':
        council = ['관리자', '부관리자', '보안총책임자', '대통령급']
        if user_grade not in council:
            flash("3심은 최고 회의 구성원만이 판결할 수 있습니다.")
            return redirect(url_for('legal.view_case', case_id=case_id))

    case['status'] = f"tier{tier}_{result}"

    if result == 'guilty' and tier == '3':
        # Final enforcement as per Criminal Procedure Act
        EconomyService.update_user_assets(case['target'], -fine, f"재판 최종 판결 벌금 ({case_id})")
        CSVManager.add_penalty(case['target'], f"재판 최종 판결 ({case_id})", penalty_score, session['user']['name'])
        case['status'] = 'final_guilty'
    elif result == 'innocent' and tier == '3':
        case['status'] = 'final_innocent'

    CSVManager.write('data/complaints.csv', complaints, ['id', 'reporter', 'target', 'reason', 'law_title', 'status', 'timestamp'])

    # Log criminal record if final guilty
    if case['status'] == 'final_guilty':
        record = {
            'user': case['target'],
            'crime': case['law_title'],
            'verdict': f"벌금 {fine}, 벌점 {penalty_score}",
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        CSVManager.append('data/criminal_records.csv', record, ['user', 'crime', 'verdict', 'timestamp'])

    flash(f"{tier}심 판결이 등록되었습니다.")
    return redirect(url_for('legal.view_case', case_id=case_id))

@legal_bp.route('/ai_prompt/<case_id>')
@login_required
def generate_ai_prompt(case_id):
    # Requirements: "원고와 피고 둘의 주장까지 입력받아서 프롬프트를 관리자한테 보내주면 될것 같ㅌ아. 관리자가 제출은 할게"
    complaints = CSVManager.read('data/complaints.csv')
    case = next((c for c in complaints if c['id'] == case_id), None)

    # Constructing a simulated prompt for the admin to copy-paste into an AI
    prompt = f"""
    [코리아민국 2심 재판 AI 판결 요청]

    사건 개요: {case['reason']}
    적용 법률: {case['law_title']}
    피고인: {case['target']}
    고발인: {case['reporter']}

    위 정보와 코리아민국 헌법 및 형법에 근거하여 2심 판결을 내려주십시오.
    판결 형식: [유죄/무죄/재심], 벌금 액수, 벌점 점수
    """
    return render_template('legal/ai_prompt.html', prompt=prompt, case_id=case_id)
