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
