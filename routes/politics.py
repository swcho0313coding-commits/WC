from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from utils.csv_manager import CSVManager
from utils.auth import login_required, permission_required
from datetime import datetime
import uuid
import os

politics_bp = Blueprint('politics', __name__)

@politics_bp.route('/')
@login_required
@permission_required('politics')
def index():
    parties = CSVManager.read('data/parties.csv')

    # Placeholder Replacement for Country Name
    country = CSVManager.get_config('country_name')
    for p in parties:
        p['name'] = p['name'].replace('{국가이름}', country)

    elections = CSVManager.read('data/elections.csv')
    current_election = next((e for e in elections if e['status'] != 'completed'), None)

    users = CSVManager.read('data/users.csv')
    president = next((u for u in users if u['grade'] == '대통령급'), None)
    cabinet = [u for u in users if u['grade'] in ['국무총리급', '행정 1등급', '입법 1등급', '사법 1등급']]

    return render_template('politics/index.html',
                           parties=parties,
                           current_election=current_election,
                           president=president,
                           cabinet=cabinet)

@politics_bp.route('/register_candidate/<election_id>', methods=['POST'])
@login_required
def register_candidate(election_id):
    user = session['user']
    # Check registration fee (300,000,000)
    fee = int(CSVManager.get_config('election_fee') or 300000000)

    from services.economy import EconomyService
    success, msg = EconomyService.update_user_assets(user['name'], -fee, f"대통령 선거 후보 등록금 납부 ({election_id})")
    if not success:
        flash(f"등록금이 부족합니다. (필요: {fee})")
        return redirect(url_for('politics.index'))

    elections = CSVManager.read('data/elections.csv')
    for e in elections:
        if e['id'] == election_id:
            candidates = e['candidates'].split(',') if e['candidates'] else []
            if user['name'] not in candidates:
                candidates.append(user['name'])
                e['candidates'] = ','.join(candidates)
                break

    CSVManager.write('data/elections.csv', elections,
                     ['id', 'type', 'start_date', 'end_date', 'candidates', 'status', 'winner'])
    flash("대통령 후보로 등록되었습니다.")
    return redirect(url_for('politics.index'))

@politics_bp.route('/vote/<election_id>', methods=['POST'])
@login_required
def vote(election_id):
    candidate = request.form.get('candidate')
    user_name = session['user']['name']

    # Check if already voted
    votes = CSVManager.read('data/votes.csv')
    if any(v['election_id'] == election_id and v['voter'] == user_name for v in votes):
        flash("이미 투표하셨습니다.")
        return redirect(url_for('politics.index'))

    new_vote = {
        'election_id': election_id,
        'voter': user_name,
        'candidate': candidate,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    CSVManager.append('data/votes.csv', new_vote, ['election_id', 'voter', 'candidate', 'timestamp'])
    flash("투표가 완료되었습니다.")
    return redirect(url_for('politics.index'))

@politics_bp.route('/create_party', methods=['GET', 'POST'])
@login_required
def create_party():
    if request.method == 'POST':
        party_name = request.form.get('name')
        description = request.form.get('description')

        new_party = {
            'name': party_name,
            'founder': session['user']['name'],
            'description': description,
            'members': session['user']['name'],
            'status': 'pending', # Needs admin/higher approval
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        CSVManager.append('data/parties.csv', new_party, ['name', 'founder', 'description', 'members', 'status', 'timestamp'])
        flash("정당 창설 신청이 완료되었습니다.")
        return redirect(url_for('politics.index'))
    return render_template('politics/create_party.html')

@politics_bp.route('/appoint_cabinet', methods=['POST'])
@login_required
@permission_required('appoint_cabinet')
def appoint_cabinet():
    target_user = request.form.get('user')
    target_grade = request.form.get('grade')

    users = CSVManager.read('data/users.csv')
    for u in users:
        if u['name'] == target_user:
            u['grade'] = target_grade
            break

    CSVManager.write('data/users.csv', users, ['name', 'login_id', 'password', 'birth', 'grade', 'phone', 'resident_id', 'school_info', 'assets', 'status', 'credit_score'])
    flash(f"{target_user}님을 {target_grade}으로 지명하였습니다.")
    return redirect(url_for('politics.index'))

@politics_bp.route('/propose_law', methods=['GET', 'POST'])
@login_required
def propose_law():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')

        new_law = {
            'id': str(uuid.uuid4()),
            'title': title,
            'content': content,
            'proposer': session['user']['name'],
            'status': 'pending_legislative',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        CSVManager.append('data/proposed_laws.csv', new_law, ['id', 'title', 'content', 'proposer', 'status', 'timestamp'])
        flash("법률안이 발의되었습니다.")
        return redirect(url_for('politics.index'))
    return render_template('politics/propose_law.html')

@politics_bp.route('/review_laws')
@login_required
def review_laws():
    laws = CSVManager.read('data/proposed_laws.csv')
    return render_template('politics/review_laws.html', laws=laws)

@politics_bp.route('/vote_law/<law_id>', methods=['POST'])
@login_required
def vote_law(law_id):
    if '입법' not in session['user']['grade'] and session['user']['grade'] != '관리자':
        flash("입법부 소속만 투표할 수 있습니다.")
        return redirect(url_for('politics.review_laws'))

    vote = request.form.get('vote')
    laws = CSVManager.read('data/proposed_laws.csv')
    for l in laws:
        if l['id'] == law_id:
            if vote == 'for':
                l['status'] = 'pending_president'
                flash("법안이 가결되어 대통령에게 이송되었습니다.")
            else:
                l['status'] = 'rejected_legislative'
                flash("법안이 부결되었습니다.")
            break
    CSVManager.write('data/proposed_laws.csv', laws, ['id', 'title', 'content', 'proposer', 'status', 'timestamp'])
    return redirect(url_for('politics.review_laws'))

@politics_bp.route('/budget', methods=['GET', 'POST'])
@login_required
def budget():
    if request.method == 'POST':
        # Create budget proposal
        title = request.form.get('title')
        amount = int(request.form.get('amount'))
        purpose = request.form.get('purpose')

        new_budget = {
            'id': str(uuid.uuid4()),
            'title': title,
            'amount': str(amount),
            'purpose': purpose,
            'proposer': session['user']['name'],
            'status': 'pending',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        CSVManager.append('data/budgets.csv', new_budget, ['id', 'title', 'amount', 'purpose', 'proposer', 'status', 'timestamp'])
        flash("예산안이 제출되었습니다.")
        return redirect(url_for('politics.budget'))

    budgets = CSVManager.read('data/budgets.csv')
    return render_template('politics/budget.html', budgets=budgets)

@politics_bp.route('/parties')
@login_required
def parties_list():
    parties = CSVManager.read('data/parties.csv')
    return render_template('politics/parties.html', parties=parties)

@politics_bp.route('/vote_impeachment', methods=['POST'])
@login_required
def vote_impeachment():
    # Only Legislative Rank 1 can vote as per standard procedures or custom
    if '입법 1등급' not in session['user']['grade'] and session['user']['grade'] != '관리자':
        flash("입법 1등급만 탄핵 투표가 가능합니다.")
        return redirect(url_for('politics.index'))

    vote = request.form.get('vote')
    # Save to impeachment_votes.csv
    flash("탄핵 투표가 접수되었습니다.")
    return redirect(url_for('politics.index'))

@politics_bp.route('/manage_cabinet')
@login_required
@permission_required('appoint_cabinet')
def manage_cabinet():
    users = CSVManager.read('data/users.csv')
    cabinet_candidates = [u for u in users if u['status'] == 'active']
    return render_template('politics/manage_cabinet.html', users=cabinet_candidates)

@politics_bp.route('/approve_budget/<budget_id>', methods=['POST'])
@login_required
def approve_budget(budget_id):
    if session['user']['grade'] not in ['행정 1등급', '관리자', '대통령급']:
        flash("예산 승인 권한이 없습니다.")
        return redirect(url_for('politics.budget'))

    action = request.form.get('action') # approve, reject
    budgets = CSVManager.read('data/budgets.csv')

    for b in budgets:
        if b['id'] == budget_id:
            if action == 'approve':
                # Move money from Treasury to... (tracked in treasury.csv)
                amount = int(b['amount'])
                treasury = CSVManager.read('data/treasury.csv')
                current_balance = int(treasury[-1]['balance']) if treasury else 0

                if current_balance < amount:
                    flash("국고 잔액이 부족하여 승인할 수 없습니다.")
                    return redirect(url_for('politics.budget'))

                b['status'] = 'approved'
                # Record transaction
                from services.economy import EconomyService
                # Assuming EconomyService handles treasury updates
                # We can manually append to treasury.csv for now or use a method
                new_entry = {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'type': 'expense',
                    'amount': str(amount),
                    'balance': str(current_balance - amount),
                    'reason': f"예산 집행: {b['title']}"
                }
                CSVManager.append('data/treasury.csv', new_entry, ['timestamp', 'type', 'amount', 'balance', 'reason'])
                flash("예산안이 최종 승인 및 집행되었습니다.")
            else:
                b['status'] = 'rejected'
                flash("예산안이 거부되었습니다.")
            break

    CSVManager.write('data/budgets.csv', budgets, ['id', 'title', 'amount', 'purpose', 'proposer', 'status', 'timestamp'])
    return redirect(url_for('politics.budget'))

@politics_bp.route('/approve_law/<law_id>', methods=['POST'])
@login_required
def approve_law(law_id):
    if session['user']['grade'] not in ['대통령급', '관리자']:
        flash("대통령만 최종 승인할 수 있습니다.")
        return redirect(url_for('politics.review_laws'))

    action = request.form.get('action')
    laws = CSVManager.read('data/proposed_laws.csv')
    for l in laws:
        if l['id'] == law_id:
            if action == 'approve':
                l['status'] = 'enacted'
                # Create the .txt file in data/laws
                safe_title = l['title'].replace('/', '_').replace('\\', '_')
                with open(f"data/laws/{safe_title}.txt", "w", encoding="utf-8-sig") as f:
                    f.write(l['content'])
                flash(f"법안 '{l['title']}'이(가) 공포되었습니다.")
            else:
                l['status'] = 'rejected_president'
                flash("거부권이 행사되었습니다.")
            break
    CSVManager.write('data/proposed_laws.csv', laws, ['id', 'title', 'content', 'proposer', 'status', 'timestamp'])
    return redirect(url_for('politics.review_laws'))
