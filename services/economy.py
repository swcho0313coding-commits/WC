from utils.csv_manager import CSVManager
from datetime import datetime

class EconomyService:
    @staticmethod
    def get_user_assets(username):
        users = CSVManager.read('data/users.csv')
        for u in users:
            if u['name'] == username:
                return int(u['assets'])
        return 0

    @staticmethod
    def update_user_assets(username, amount_change, reason):
        users = CSVManager.read('data/users.csv')
        updated = False
        new_balance = 0

        user_grade = ""
        for u in users:
            if u['name'] == username:
                user_grade = u['grade']
                # Admin/Sub-admin have unlimited money
                if user_grade in ['관리자', '부관리자']:
                    new_balance = int(u['assets']) # Doesn't really decrease/increase meaningfully but we log it
                else:
                    new_balance = int(u['assets']) + amount_change
                    if new_balance < 0:
                        return False, "잔액이 부족합니다."
                    u['assets'] = str(new_balance)
                updated = True
                break

        if updated:
            headers = ['name', 'password', 'birth', 'grade', 'phone', 'resident_id', 'school_info', 'assets', 'status', 'credit_score']
            CSVManager.write('data/users.csv', users, headers)

            # Record transaction
            log_row = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'user': username,
                'action': 'deposit' if amount_change > 0 else 'withdraw',
                'amount': str(abs(amount_change)),
                'balance': str(new_balance),
                'reason': reason
            }
            CSVManager.append('data/transactions.csv', log_row, ['timestamp', 'user', 'action', 'amount', 'balance', 'reason'])
            return True, "성공"
        return False, "사용자를 찾을 수 없습니다."

    @staticmethod
    def pay_salaries():
        users = CSVManager.read('data/users.csv')
        salaries = CSVManager.read('data/salaries.csv')
        salary_map = {s['grade']: int(s['amount']) for s in salaries}

        taxes = CSVManager.read('data/tax_config.csv')
        tax_map = {t['grade']: float(t['tax_rate']) for t in taxes}

        treasury = CSVManager.read('data/treasury.csv')
        current_treasury = int(treasury[0]['balance'])
        tax_total = 0

        for u in users:
            if u['status'] != 'active': continue

            grade = u['grade']
            if grade in salary_map:
                amount = salary_map[grade]

                # Apply tax
                tax_rate = tax_map.get(grade, 0)
                tax_amount = int(amount * tax_rate)
                net_amount = amount - tax_amount

                # Pay user
                EconomyService.update_user_assets(u['name'], net_amount, f"주급 지급 (세금 {tax_amount} 제외)")

                # Record tax
                if tax_amount > 0:
                    tax_total += tax_amount
                    tax_record = {
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'user': u['name'],
                        'amount': str(tax_amount),
                        'grade': grade
                    }
                    CSVManager.append('data/tax_records.csv', tax_record, ['timestamp', 'user', 'amount', 'grade'])

        # Update treasury with taxes
        if tax_total > 0:
            EconomyService.update_treasury(tax_total, "세금 징수")

    @staticmethod
    def update_treasury(amount_change, reason):
        rows = CSVManager.read('data/treasury.csv')
        current_balance = int(rows[0]['balance'])
        new_balance = current_balance + amount_change
        rows[0]['balance'] = str(new_balance)
        rows[0]['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        CSVManager.write('data/treasury.csv', rows, ['balance', 'last_updated'])
        # Optional: log treasury transactions
        return new_balance
