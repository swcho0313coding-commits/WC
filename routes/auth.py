from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from utils.csv_manager import CSVManager
from utils.auth import get_user_by_name
from utils.user_utils import UserUtils
import os

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')

        user = get_user_by_name(name)
        if user and user['password'] == password:
            if user['status'] == 'banned':
                flash("이 계정은 정지되었습니다.")
                CSVManager.log_activity(request.remote_addr, name, "Login attempt (banned)", "fail")
                return redirect(url_for('auth.login'))

            session['user'] = user
            CSVManager.log_activity(request.remote_addr, name, "Login", "success")
            return redirect(url_for('index'))
        else:
            flash("이름 또는 비밀번호가 틀렸습니다.")
            CSVManager.log_activity(request.remote_addr, name, "Login attempt", "fail")

    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')
        birth = request.form.get('birth') # YYYYMMDD
        school_info = request.form.get('school_info') # 학년/반

        if get_user_by_name(name):
            flash("이미 존재하는 이름입니다.")
            return redirect(url_for('auth.register'))

        phone = UserUtils.generate_phone()
        resident_id = UserUtils.generate_resident_id(birth)
        initial_assets = CSVManager.get_config('initial_assets') or '50000'

        new_user = {
            'name': name,
            'password': password,
            'birth': birth,
            'grade': '준회원',
            'phone': phone,
            'resident_id': resident_id,
            'school_info': school_info,
            'assets': initial_assets,
            'status': 'pending', # Wait for admin approval for 정회원
            'credit_score': '500'
        }

        headers = ['name', 'password', 'birth', 'grade', 'phone', 'resident_id', 'school_info', 'assets', 'status', 'credit_score']
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
