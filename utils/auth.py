from functools import wraps
from flask import session, redirect, url_for, request, flash
from utils.csv_manager import CSVManager

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_data = session.get('user')
            if not user_data:
                return redirect(url_for('auth.login'))

            # Martial Law / Emergency Restrictions
            emergency = CSVManager.read('data/emergency_records.csv')
            active_emergency = next((e for e in emergency if e['status'] == 'active'), None)

            if active_emergency:
                restricted_actions = []
                if active_emergency['type'] == '계엄령':
                    restricted_actions = ['election', 'politics', 'party_create']
                elif active_emergency['type'] == '비상사태':
                    restricted_actions = ['money_transfer'] # etc

                if permission in restricted_actions and user_data.get('grade') != '관리자':
                    flash(f"현재 {active_emergency['type']} 선포 중으로 해당 활동이 제한됩니다.")
                    return redirect(url_for('index'))

            user_grade = user_data.get('grade')
            permissions_list = CSVManager.read('data/permissions.csv')

            user_permissions = []
            for p in permissions_list:
                if p['grade'] == user_grade:
                    user_permissions = p['permissions'].split(',')
                    break

            if 'all' in user_permissions or permission in user_permissions:
                return f(*args, **kwargs)
            else:
                flash("권한이 없습니다.")
                CSVManager.log_activity(request.remote_addr, user_data.get('name'), f"Unauthorized access attempt: {permission}", "fail")
                return redirect(url_for('index'))
        return decorated_function
    return decorator

def get_user_by_name(name):
    users = CSVManager.read('data/users.csv')
    for u in users:
        if u['name'] == name:
            return u
    return None
