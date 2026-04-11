from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from utils.csv_manager import CSVManager
from utils.auth import login_required
from services.economy import EconomyService
from datetime import datetime, timedelta

bank_bp = Blueprint('bank', __name__)

@bank_bp.route('/')
@login_required
def index():
    user = session['user']
    loans = CSVManager.read('data/loans.csv')
    user_loans = [l for l in loans if l['user'] == user['name']]
    return render_template('bank/index.html', loans=user_loans)

@bank_bp.route('/loan', methods=['POST'])
@login_required
def apply_loan():
    amount = int(request.form.get('amount'))
    user = session['user']

    # Credit score check (very simple)
    if int(user['credit_score']) < 300:
        flash("신용 등급이 낮아 대출이 불가능합니다.")
        return redirect(url_for('bank.index'))

    new_loan = {
        'user': user['name'],
        'amount': str(amount),
        'interest_rate': '0.05',
        'due_date': (datetime.now() + timedelta(weeks=1)).strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'active'
    }
    CSVManager.append('data/loans.csv', new_loan, ['user', 'amount', 'interest_rate', 'due_date', 'status'])
    EconomyService.update_user_assets(user['name'], amount, "은행 대출 실행")
    flash(f"{amount} 크레딧 대출이 승인되었습니다.")
    return redirect(url_for('bank.index'))

@bank_bp.route('/transfer', methods=['POST'])
@login_required
def transfer():
    recipient_name = request.form.get('recipient')
    amount = int(request.form.get('amount'))
    sender = session['user']

    if sender['name'] == recipient_name:
        flash("자신에게는 송금할 수 없습니다.")
        return redirect(url_for('bank.index'))

    recipient = get_user_by_name(recipient_name)
    if not recipient:
        flash("수취인을 찾을 수 없습니다.")
        return redirect(url_for('bank.index'))

    success, msg = EconomyService.update_user_assets(sender['name'], -amount, f"{recipient_name}에게 송금")
    if success:
        EconomyService.update_user_assets(recipient_name, amount, f"{sender['name']}로부터 송금")
        flash(f"{recipient_name}님께 {amount} 크레딧을 성공적으로 송금했습니다.")
    else:
        flash(msg)
    return redirect(url_for('bank.index'))

def get_user_by_name(name):
    users = CSVManager.read('data/users.csv')
    for u in users:
        if u['name'] == name:
            return u
    return None

@bank_bp.route('/repay/<int:loan_idx>', methods=['POST'])
@login_required
def repay(loan_idx):
    loans = CSVManager.read('data/loans.csv')
    loan = loans[loan_idx]
    user = session['user']

    amount_to_pay = int(float(loan['amount']) * (1 + float(loan['interest_rate'])))

    success, msg = EconomyService.update_user_assets(user['name'], -amount_to_pay, "대출 상환")
    if success:
        loan['status'] = 'repaid'
        CSVManager.write('data/loans.csv', loans, ['user', 'amount', 'interest_rate', 'due_date', 'status'])
        flash("대출 상환이 완료되었습니다.")
    else:
        flash(msg)
    return redirect(url_for('bank.index'))
