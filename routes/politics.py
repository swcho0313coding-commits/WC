from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from utils.csv_manager import CSVManager
from utils.auth import login_required, permission_required
from services.economy import EconomyService
from datetime import datetime, timedelta

politics_bp = Blueprint('politics', __name__)

@politics_bp.route('/')
@login_required
def index():
    election = CSVManager.read('data/elections.csv')
    active_election = next((e for e in election if e['status'] == 'active'), None)

    parties = CSVManager.read('data/parties.csv')

    return render_template('politics/index.html', election=active_election, parties=parties)

@politics_bp.route('/parties')
@login_required
def parties_list():
    parties = CSVManager.read('data/parties.csv')
    return render_template('politics/parties.html', parties=parties)

@politics_bp.route('/create_party', methods=['GET', 'POST'])
@login_required
def create_party():
    if request.method == 'POST':
        name = request.form.get('name')
        # Check if already exists
        parties = CSVManager.read('data/parties.csv')
        if any(p['name'] == name for p in parties):
            flash("이미 존재하는 정당 이름입니다.")
            return redirect(url_for('politics.create_party'))

        new_party = {
            'name': name,
            'founder': session['user']['name'],
            'members': session['user']['name'],
            'status': 'pending',
            'seats': '0'
        }
        CSVManager.append('data/parties.csv', new_party, ['name', 'founder', 'members', 'status', 'seats'])
        flash("정당 창설 신청이 완료되었습니다. 승인을 기다려주세요.")
        return redirect(url_for('politics.parties_list'))

    return render_template('politics/create_party.html')

@politics_bp.route('/election/register', methods=['POST'])
@login_required
def register_candidate():
    user = session['user']
    fee = int(CSVManager.get_config('election_fee') or 300000000)

    elections = CSVManager.read('data/elections.csv')
    active = next((e for e in elections if e['status'] == 'registration'), None)

    if not active:
        flash("현재 후보 등록 기간이 아닙니다.")
        return redirect(url_for('politics.index'))

    if int(user['assets']) < fee:
        flash("등록금이 부족합니다.")
        return redirect(url_for('politics.index'))

    success, msg = EconomyService.update_user_assets(user['name'], -fee, "대통령 선거 등록금 납부")
    if success:
        candidates = active['candidates'].split(',') if active['candidates'] else []
        if user['name'] not in candidates:
            candidates.append(user['name'])
            active['candidates'] = ','.join(candidates)
            CSVManager.write('data/elections.csv', elections, ['id', 'type', 'start_date', 'end_date', 'candidates', 'status', 'winner'])
            flash("선거 후보로 등록되었습니다.")
        else:
            flash("이미 등록된 후보입니다.")
    else:
        flash(msg)

    return redirect(url_for('politics.index'))

@politics_bp.route('/election/vote', methods=['POST'])
@login_required
def vote():
    candidate = request.form.get('candidate')
    voter = session['user']['name']

    elections = CSVManager.read('data/elections.csv')
    active = next((e for e in elections if e['status'] == 'voting'), None)

    if not active:
        flash("현재 투표 기간이 아닙니다.")
        return redirect(url_for('politics.index'))

    votes = CSVManager.read('data/votes.csv')
    if any(v['election_id'] == active['id'] and v['voter'] == voter for v in votes):
        flash("이미 투표하셨습니다.")
        return redirect(url_for('politics.index'))

    new_vote = {
        'election_id': active['id'],
        'voter': voter,
        'candidate': candidate,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    CSVManager.append('data/votes.csv', new_vote, ['election_id', 'voter', 'candidate', 'timestamp'])
    flash(f"{candidate} 후보에게 투표하였습니다.")
    return redirect(url_for('politics.index'))

@politics_bp.route('/laws/propose', methods=['GET', 'POST'])
@login_required
@permission_required('edit_csv') # 입법 1~7등급 (simplified)
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
            'votes_for': '0',
            'votes_against': '0',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        CSVManager.append('data/proposed_laws.csv', new_law, ['id', 'title', 'content', 'proposer', 'status', 'votes_for', 'votes_against', 'timestamp'])
        flash("법안이 발의되었습니다.")
        return redirect(url_for('politics.index'))
    return render_template('politics/propose_law.html')

@politics_bp.route('/laws/review')
@login_required
def review_laws():
    proposed = CSVManager.read('data/proposed_laws.csv')
    return render_template('politics/review_laws.html', laws=proposed)

@politics_bp.route('/laws/vote/<law_id>', methods=['POST'])
@login_required
def vote_law(law_id):
    # Simplified: only 입법 grades can vote
    if '입법' not in session['user']['grade']:
        flash("입법부 권한이 필요합니다.")
        return redirect(url_for('politics.review_laws'))

    vote_val = request.form.get('vote')
    proposed = CSVManager.read('data/proposed_laws.csv')
    for p in proposed:
        if p['id'] == law_id:
            if vote_val == 'for': p['votes_for'] = str(int(p['votes_for']) + 1)
            else: p['votes_against'] = str(int(p['votes_against']) + 1)

            # Transition to president if enough votes (simplified: > 1 vote)
            if int(p['votes_for']) >= 1:
                p['status'] = 'pending_president'
            break
    CSVManager.write('data/proposed_laws.csv', proposed, ['id', 'title', 'content', 'proposer', 'status', 'votes_for', 'votes_against', 'timestamp'])
    return redirect(url_for('politics.review_laws'))

@politics_bp.route('/laws/approve/<law_id>', methods=['POST'])
@login_required
def approve_law(law_id):
    if session['user']['grade'] != '대통령급':
        flash("대통령 권한이 필요합니다.")
        return redirect(url_for('politics.review_laws'))

    action = request.form.get('action')
    proposed = CSVManager.read('data/proposed_laws.csv')
    for p in proposed:
        if p['id'] == law_id:
            if action == 'approve':
                p['status'] = 'approved'
                # Add to final laws.csv
                new_law = {
                    'id': p['id'],
                    'name': p['title'],
                    'content': p['content'],
                    'punishment': '재판 결과에 따름'
                }
                CSVManager.append('data/laws.csv', new_law, ['id', 'name', 'content', 'punishment'])
                flash("법안이 최종 승인 및 공포되었습니다.")
            else:
                p['status'] = 'rejected'
                flash("거부권이 행사되었습니다.")
            break
    CSVManager.write('data/proposed_laws.csv', proposed, ['id', 'title', 'content', 'proposer', 'status', 'votes_for', 'votes_against', 'timestamp'])
    return redirect(url_for('politics.review_laws'))

@politics_bp.route('/impeachment/propose', methods=['POST'])
@login_required
@permission_required('edit_csv') # 입법 1등급 권한 (simplified)
def propose_impeachment():
    target = request.form.get('target') # Should be the current president
    reason = request.form.get('reason')

    new_imp = {
        'target': target,
        'proposer': session['user']['name'],
        'reason': reason,
        'status': 'voting',
        'votes_for': '0',
        'votes_against': '0',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    CSVManager.append('data/impeachment.csv', new_imp, ['target', 'proposer', 'reason', 'status', 'votes_for', 'votes_against', 'timestamp'])
    flash("탄핵안이 발의되었습니다.")
    return redirect(url_for('politics.index'))

@politics_bp.route('/impeachment/vote', methods=['POST'])
@login_required
def vote_impeachment():
    vote_val = request.form.get('vote')
    imps = CSVManager.read('data/impeachment.csv')
    updated = False
    for i in imps:
        if i['status'] == 'voting':
            if vote_val == 'for': i['votes_for'] = str(int(i['votes_for']) + 1)
            else: i['votes_against'] = str(int(i['votes_against']) + 1)

            # 2/3 majority check (simplified: 2 votes for now)
            if int(i['votes_for']) >= 2:
                i['status'] = 'impeached'
                # Presidential Succession
                users = CSVManager.read('data/users.csv')
                for u in users:
                    if u['name'] == i['target']:
                        u['grade'] = '국민 9등급' # Demoted
                        u['status'] = 'banned'
                    if u['grade'] == '국무총리급':
                        u['grade'] = '대통령급' # Succession
                CSVManager.write('data/users.csv', users, ['name', 'password', 'birth', 'grade', 'phone', 'resident_id', 'school_info', 'assets', 'status', 'credit_score'])
            updated = True
            break
    if updated:
        CSVManager.write('data/impeachment.csv', imps, ['target', 'proposer', 'reason', 'status', 'votes_for', 'votes_against', 'timestamp'])
        flash("탄핵 투표가 반영되었습니다.")
    return redirect(url_for('politics.index'))
