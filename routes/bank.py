from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from utils.csv_manager import CSVManager
from services.economy import EconomyService
from utils.auth import login_required
from datetime import datetime

bank_bp = Blueprint('bank', __name__)

@bank_bp.route('/')
@login_required
def index():
    users = CSVManager.read('data/users.csv')
    user = next((u for u in users if u['name'] == session['user']['name']), None)
    transactions = CSVManager.read('data/transactions.csv')
    my_transactions = [t for t in transactions if t['user'] == user['name']][::-1][:10]

    loans = CSVManager.read('data/loans.csv')
    my_loans = [l for l in loans if l['user'] == user['name']]

    return render_template('bank/index.html', user=user, transactions=my_transactions, loans=my_loans)

@bank_bp.route('/transfer', methods=['POST'])
@login_required
def transfer():
    recipient_name = request.form.get('recipient')
    recipient_phone = request.form.get('phone')
    amount = int(request.form.get('amount'))

    if amount <= 0:
        flash("유효하지 않은 금액입니다.")
        return redirect(url_for('bank.index'))

    # Verify Recipient Identity
    users = CSVManager.read('data/users.csv')
    recipient = next((u for u in users if u['name'] == recipient_name and u['phone'] == recipient_phone), None)

    if not recipient:
        flash("수취인 정보(이름/전화번호)가 일치하지 않습니다.")
        return redirect(url_for('bank.index'))

    sender_name = session['user']['name']
    if sender_name == recipient_name:
        flash("본인에게 송금할 수 없습니다.")
        return redirect(url_for('bank.index'))

    success, msg = EconomyService.update_user_assets(sender_name, -amount, f"{recipient_name}({recipient_phone})에게 송금")
    if success:
        EconomyService.update_user_assets(recipient_name, amount, f"{sender_name}로부터 송금")
        flash(f"{recipient_name}님께 {amount} {CSVManager.get_config('currency_name')}을 송금했습니다.")
    else:
        flash(msg)

    return redirect(url_for('bank.index'))

@bank_bp.route('/loan', methods=['POST'])
@login_required
def apply_loan():
    amount = int(request.form.get('amount'))
    user_name = session['user']['name']

    users = CSVManager.read('data/users.csv')
    user = next((u for u in users if u['name'] == user_name), None)
    credit_score = int(user.get('credit_score', 0))

    if amount > credit_score * 100:
        flash("신용등급 한도를 초과했습니다.")
        return redirect(url_for('bank.index'))

    new_loan = {
        'user': user_name,
        'amount': str(amount),
        'interest_rate': '0.05',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'active'
    }
    CSVManager.append('data/loans.csv', new_loan, ['user', 'amount', 'interest_rate', 'timestamp', 'status'])
    EconomyService.update_user_assets(user_name, amount, "은행 대출 실행")

    flash(f"{amount} {CSVManager.get_config('currency_name')} 대출이 완료되었습니다.")
    return redirect(url_for('bank.index'))

@bank_bp.route('/repay', methods=['POST'])
@login_required
def repay():
    val = request.form.get('amount')
    if not val:
        flash("상환 금액을 입력하세요.")
        return redirect(url_for('bank.index'))

    amount = int(val)
    user_name = session['user']['name']

    success, msg = EconomyService.update_user_assets(user_name, -amount, "대출금 상환")
    if success:
        # Update loans.csv (simplified: reduce first active loan)
        loans = CSVManager.read('data/loans.csv')
        for l in loans:
            if l['user'] == user_name and l['status'] == 'active':
                current_loan = int(l['amount'])
                if current_loan <= amount:
                    l['amount'] = '0'
                    l['status'] = 'repaid'
                else:
                    l['amount'] = str(current_loan - amount)
                break
        CSVManager.write('data/loans.csv', loans, ['user', 'amount', 'interest_rate', 'timestamp', 'status'])
        flash("대출금이 상환되었습니다.")
    else:
        flash(msg)
    return redirect(url_for('bank.index'))
