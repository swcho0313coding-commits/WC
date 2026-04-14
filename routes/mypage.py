from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from utils.csv_manager import CSVManager
from utils.auth import login_required, get_user_by_name
from utils.user_utils import UserUtils
from datetime import datetime
import os

mypage_bp = Blueprint('mypage', __name__)

@mypage_bp.route('/')
@login_required
def index():
    user = session['user']
    user = get_user_by_name(user['name'])
    session['user'] = user

    id_card_url = f"uploads/id_cards/{user['name']}_id.png"
    medals = CSVManager.read('data/medals.csv')
    user_medals = [m for m in medals if m['user'] == user['name']]

    transactions = CSVManager.read('data/transactions.csv')
    my_transactions = [t for t in transactions if t['user'] == user['name']][::-1]

    return render_template('mypage/index.html', user=user, id_card_url=id_card_url, medals=user_medals, transactions=my_transactions)

@mypage_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        new_password = request.form.get('password')
        users = CSVManager.read('data/users.csv')
        for u in users:
            if u['name'] == session['user']['name']:
                u['password'] = new_password
                break
        CSVManager.write('data/users.csv', users, ['name', 'login_id', 'password', 'birth', 'grade', 'phone', 'resident_id', 'school_info', 'assets', 'status', 'credit_score', 'last_update_year'])
        flash("비밀번호가 변경되었습니다.")
        return redirect(url_for('mypage.index'))
    return render_template('mypage/change_password.html')

@mypage_bp.route('/update_info', methods=['GET', 'POST'])
@login_required
def update_info():
    if request.method == 'POST':
        school_info = request.form.get('school_info')
        users = CSVManager.read('data/users.csv')
        now = datetime.now()
        for u in users:
            if u['name'] == session['user']['name']:
                u['school_info'] = school_info
                u['last_update_year'] = str(now.year)
                # Regenerate Resident ID and Card
                u['resident_id'] = UserUtils.generate_resident_id(u['name'], school_info)
                UserUtils.create_id_card(u)
                break
        CSVManager.write('data/users.csv', users, ['name', 'login_id', 'password', 'birth', 'grade', 'phone', 'resident_id', 'school_info', 'assets', 'status', 'credit_score', 'last_update_year'])

        # Update session to avoid immediate redirect in before_request
        for u in users:
            if u['name'] == session['user']['name']:
                session['user'] = u
                break

        # Log that this user has updated info
        CSVManager.log_activity(request.remote_addr, session['user']['name'], "Updated School Info", "success")

        flash("학년/반 정보가 성공적으로 수정되었습니다.")
        return redirect(url_for('index'))

    return render_template('mypage/update_info.html')
