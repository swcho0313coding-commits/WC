from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from utils.csv_manager import CSVManager
from utils.auth import get_user_by_name
from utils.user_utils import UserUtils
import os

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_id = request.form.get('login_id')
        password = request.form.get('password')

        users = CSVManager.read('data/users.csv')
        user = next((u for u in users if u['login_id'] == login_id), None)

        if user and user['password'] == password:
            if user['status'] == 'banned':
                flash("이 계정은 정지되었습니다.")
                CSVManager.log_activity(request.remote_addr, user['name'], "Login attempt (banned)", "fail")
                return redirect(url_for('auth.login'))

            session['user'] = user
            CSVManager.log_activity(request.remote_addr, user['name'], "Login", "success")
            return redirect(url_for('index'))
        else:
            flash("아이디 또는 비밀번호가 틀렸습니다.")
            CSVManager.log_activity(request.remote_addr, "unknown", f"Login attempt fail (ID: {login_id})", "fail")

    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        login_id = request.form.get('login_id')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        birth = request.form.get('birth')
        school_info = request.form.get('school_info')

        if password != password_confirm:
            flash("비밀번호가 일치하지 않습니다.")
            return redirect(url_for('auth.register'))

        users = CSVManager.read('data/users.csv')
        if any(u['login_id'] == login_id for u in users):
            flash("이미 존재하는 ID입니다.")
            return redirect(url_for('auth.register'))

        # Generate Phone (check uniqueness)
        existing_phones = [u['phone'] for u in users]
        phone = UserUtils.generate_phone()
        while phone in existing_phones:
            phone = UserUtils.generate_phone()

        resident_id = UserUtils.generate_resident_id(name, school_info)
        initial_assets = CSVManager.get_config('initial_assets') or '50000'

        new_user = {
            'name': name,
            'login_id': login_id,
            'password': password,
            'birth': birth,
            'grade': '준회원',
            'phone': phone,
            'resident_id': resident_id,
            'school_info': school_info,
            'assets': initial_assets,
            'status': 'pending',
            'credit_score': '500',
            'last_update_year': '0'
        }

        headers = ['name', 'login_id', 'password', 'birth', 'grade', 'phone', 'resident_id', 'school_info', 'assets', 'status', 'credit_score', 'last_update_year']
        CSVManager.append('data/users.csv', new_user, headers)

        # Generate ID card
        UserUtils.create_id_card(new_user)

        flash("가입 신청이 완료되었습니다. 관리자 승인 후 이용 가능합니다.")
        CSVManager.log_activity(request.remote_addr, name, "Register", "success")
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    user = session.get('user')
    if user:
        CSVManager.log_activity(request.remote_addr, user['name'], "Logout", "success")
    session.pop('user', None)
    return redirect(url_for('auth.login'))
