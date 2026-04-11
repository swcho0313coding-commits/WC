from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from utils.csv_manager import CSVManager
from utils.auth import login_required
from services.economy import EconomyService
import random

games_bp = Blueprint('games', __name__)

@games_bp.route('/')
@login_required
def index():
    return render_template('games/index.html')

@games_bp.route('/rps', methods=['GET', 'POST'])
@login_required
def rps():
    if request.method == 'POST':
        bet = int(request.form.get('bet'))
        user_choice = request.form.get('choice')
        choices = ['가위', '바위', '보']
        com_choice = random.choice(choices)

        user = session['user']
        if int(user['assets']) < bet:
            flash("자산이 부족합니다.")
            return redirect(url_for('games.rps'))

        result = ""
        win = False
        draw = False

        if user_choice == com_choice:
            result = "무승부"
            draw = True
        elif (user_choice == '가위' and com_choice == '보') or \
             (user_choice == '바위' and com_choice == '가위') or \
             (user_choice == '보' and com_choice == '바위'):
            result = "승리!"
            win = True
        else:
            result = "패배..."

        if win:
            EconomyService.update_user_assets(user['name'], bet, f"가위바위보 승리 vs {com_choice}")
        elif not draw:
            EconomyService.update_user_assets(user['name'], -bet, f"가위바위보 패배 vs {com_choice}")

        return render_template('games/rps_result.html', user_choice=user_choice, com_choice=com_choice, result=result)

    return render_template('games/rps.html')

@games_bp.route('/lottery', methods=['GET', 'POST'])
@login_required
def lottery():
    if request.method == 'POST':
        user = session['user']
        price = int(CSVManager.get_config('lottery_price') or 50000)

        if int(user['assets']) < price:
            flash("자산이 부족합니다.")
            return redirect(url_for('games.lottery'))

        success, msg = EconomyService.update_user_assets(user['name'], -price, "복권 구매")
        if success:
            EconomyService.update_treasury(price, "복권 판매 수익")
            flash("복권 구매 완료!")
        else:
            flash(msg)

    return render_template('games/lottery.html')

@games_bp.route('/slots', methods=['GET', 'POST'])
@login_required
def slots():
    if request.method == 'POST':
        bet = int(request.form.get('bet'))
        user = session['user']
        if int(user['assets']) < bet:
            flash("자산이 부족합니다.")
            return redirect(url_for('games.slots'))

        symbols = ['🍒', '🍋', '🔔', '💎', '7️⃣']
        reel1 = random.choice(symbols)
        reel2 = random.choice(symbols)
        reel3 = random.choice(symbols)

        result_msg = f"{reel1} | {reel2} | {reel3}"
        if reel1 == reel2 == reel3:
            multiplier = 10 if reel1 == '7️⃣' else 5
            win_amount = bet * multiplier
            EconomyService.update_user_assets(user['name'], win_amount, f"슬롯머신 잭팟! ({reel1})")
            flash(f"잭팟! {win_amount} 크레딧 획득!")
        else:
            EconomyService.update_user_assets(user['name'], -bet, "슬롯머신 패배")
            flash("아쉽네요...")

        return render_template('games/slots_result.html', result_msg=result_msg)

    return render_template('games/slots.html')

@games_bp.route('/blackjack', methods=['GET', 'POST'])
@login_required
def blackjack():
    # Simple blackjack logic
    if request.method == 'POST':
        action = request.form.get('action')
        bet = int(session.get('bj_bet', 0))
        user = session['user']

        if action == 'start':
            bet = int(request.form.get('bet', 1000))
            if int(user['assets']) < bet:
                flash("자산이 부족합니다.")
                return redirect(url_for('games.blackjack'))
            session['bj_bet'] = bet
            session['bj_user_hand'] = [random.randint(1, 11), random.randint(1, 11)]
            session['bj_com_hand'] = [random.randint(1, 11), random.randint(1, 11)]
            return render_template('games/blackjack_play.html')

        elif action == 'hit':
            session['bj_user_hand'].append(random.randint(1, 11))
            if sum(session['bj_user_hand']) > 21:
                EconomyService.update_user_assets(user['name'], -bet, "블랙잭 버스트 패배")
                flash(f"버스트! 총합 {sum(session['bj_user_hand'])}. 패배하셨습니다.")
                return redirect(url_for('games.blackjack'))
            return render_template('games/blackjack_play.html')

        elif action == 'stay':
            user_total = sum(session['bj_user_hand'])
            com_hand = session['bj_com_hand']
            while sum(com_hand) < 17:
                com_hand.append(random.randint(1, 11))
            com_total = sum(com_hand)

            if com_total > 21 or user_total > com_total:
                EconomyService.update_user_assets(user['name'], bet, f"블랙잭 승리 (딜러 {com_total})")
                flash(f"승리! 딜러: {com_total}, 당신: {user_total}")
            elif user_total < com_total:
                EconomyService.update_user_assets(user['name'], -bet, f"블랙잭 패배 (딜러 {com_total})")
                flash(f"패배... 딜러: {com_total}, 당신: {user_total}")
            else:
                flash("무승부입니다.")
            return redirect(url_for('games.blackjack'))

    return render_template('games/blackjack.html')

@games_bp.route('/hilo', methods=['GET', 'POST'])
@login_required
def hilo():
    if request.method == 'POST':
        bet = int(request.form.get('bet', 1000))
        guess = request.form.get('guess') # hi or lo
        current_card = int(request.form.get('current_card'))
        next_card = random.randint(1, 13)

        user = session['user']
        if int(user['assets']) < bet:
            flash("자산이 부족합니다.")
            return redirect(url_for('games.hilo'))

        win = False
        if (guess == 'hi' and next_card > current_card) or (guess == 'lo' and next_card < current_card):
            win = True

        if win:
            EconomyService.update_user_assets(user['name'], bet, f"하이로우 승리 ({current_card} -> {next_card})")
            flash(f"정답! 다음 카드는 {next_card}였습니다. {bet} 크레딧 획득!")
        else:
            EconomyService.update_user_assets(user['name'], -bet, f"하이로우 패배 ({current_card} -> {next_card})")
            flash(f"틀렸습니다. 다음 카드는 {next_card}였습니다.")

    current_card = random.randint(1, 13)
    return render_template('games/hilo.html', current_card=current_card)

@games_bp.route('/gacha', methods=['GET', 'POST'])
@login_required
def gacha():
    if request.method == 'POST':
        user = session['user']
        price = 5000
        if int(user['assets']) < price:
            flash("자산이 부족합니다.")
            return redirect(url_for('games.gacha'))

        EconomyService.update_user_assets(user['name'], -price, "가챠 뽑기")

        # 1% jackpot, 10% rare, 89% common
        res = random.random()
        if res < 0.01:
            prize = 500000
            msg = "축하합니다! 잭팟 당첨! 500,000 크레딧!"
        elif res < 0.11:
            prize = 20000
            msg = "레어 아이템 당첨! 20,000 크레딧!"
        else:
            prize = 1000
            msg = "커먼 아이템. 1,000 크레딧 반환."

        EconomyService.update_user_assets(user['name'], prize, f"가챠 결과: {msg}")
        flash(msg)

    return render_template('games/gacha.html')

@games_bp.route('/roulette', methods=['GET', 'POST'])
@login_required
def roulette():
    if request.method == 'POST':
        bet = int(request.form.get('bet'))
        bet_type = request.form.get('type') # red, black, even, odd, number
        bet_val = request.form.get('val')

        user = session['user']
        if int(user['assets']) < bet:
            flash("자산이 부족합니다.")
            return redirect(url_for('games.roulette'))

        result_num = random.randint(0, 36)
        red_nums = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]

        win = False
        multiplier = 1

        if bet_type == 'red' and result_num in red_nums: win = True; multiplier = 2
        elif bet_type == 'black' and result_num != 0 and result_num not in red_nums: win = True; multiplier = 2
        elif bet_type == 'even' and result_num != 0 and result_num % 2 == 0: win = True; multiplier = 2
        elif bet_type == 'odd' and result_num % 2 != 0: win = True; multiplier = 2
        elif bet_type == 'number' and str(result_num) == bet_val: win = True; multiplier = 35

        if win:
            win_amount = bet * (multiplier - 1)
            EconomyService.update_user_assets(user['name'], win_amount, f"룰렛 승리 ({result_num})")
            flash(f"당첨! 결과: {result_num}. {win_amount} 크레딧 획득!")
        else:
            EconomyService.update_user_assets(user['name'], -bet, f"룰렛 패배 ({result_num})")
            flash(f"낙첨... 결과: {result_num}")

    return render_template('games/roulette.html')

@games_bp.route('/horse', methods=['GET', 'POST'])
@login_required
def horse_racing():
    if request.method == 'POST':
        bet = int(request.form.get('bet'))
        chosen_horse = int(request.form.get('horse')) # 1-4
        user = session['user']

        if int(user['assets']) < bet:
            flash("자산이 부족합니다.")
            return redirect(url_for('games.horse_racing'))

        winner = random.randint(1, 4)
        if chosen_horse == winner:
            win_amount = bet * 3
            EconomyService.update_user_assets(user['name'], win_amount, f"경마 승리 ({winner}번 마)")
            flash(f"우승! {winner}번 마가 1등입니다! {win_amount} 크레딧 획득!")
        else:
            EconomyService.update_user_assets(user['name'], -bet, f"경마 패배 (우승: {winner}번 마)")
            flash(f"패배... 우승마는 {winner}번 마였습니다.")

    return render_template('games/horse.html')
