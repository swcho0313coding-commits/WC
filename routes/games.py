from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from utils.csv_manager import CSVManager
from services.economy import EconomyService
import random
from datetime import datetime

games_bp = Blueprint('games', __name__)

@games_bp.route('/')
def index():
    return render_template('games/index.html')

@games_bp.route('/multiplayer/dice')
def dice_battle():
    return render_template('games/multiplayer/dice.html')

@games_bp.route('/rps', methods=['GET', 'POST'])
def rps():
    if request.method == 'POST':
        bet = int(request.form.get('bet'))
        user_choice = request.form.get('choice') # rock, paper, scissors

        success, msg = EconomyService.update_user_assets(session['user']['name'], -bet, "가위바위보 베팅")
        if not success:
            flash(msg)
            return redirect(url_for('games.rps'))

        cpu_choice = random.choice(['rock', 'paper', 'scissors'])
        result = ""

        if user_choice == cpu_choice:
            result = "draw"
            EconomyService.update_user_assets(session['user']['name'], bet, "가위바위보 무승부 반환")
        elif (user_choice == 'rock' and cpu_choice == 'scissors') or \
             (user_choice == 'paper' and cpu_choice == 'rock') or \
             (user_choice == 'scissors' and cpu_choice == 'paper'):
            result = "win"
            EconomyService.update_user_assets(session['user']['name'], bet * 2, "가위바위보 승리 보상")
        else:
            result = "lose"

        return render_template('games/rps_result.html', user=user_choice, cpu=cpu_choice, result=result, bet=bet)
    return render_template('games/rps.html')

@games_bp.route('/slots', methods=['GET', 'POST'])
def slots():
    if request.method == 'POST':
        bet = int(request.form.get('bet'))
        success, msg = EconomyService.update_user_assets(session['user']['name'], -bet, "슬롯머신 베팅")
        if not success:
            flash(msg)
            return redirect(url_for('games.index'))

        symbols = ['🍒', '🍋', '🔔', '💎', '7️⃣']
        reel1 = random.choice(symbols)
        reel2 = random.choice(symbols)
        reel3 = random.choice(symbols)

        win_amount = 0
        if reel1 == reel2 == reel3:
            if reel1 == '7️⃣': win_amount = bet * 50
            elif reel1 == '💎': win_amount = bet * 20
            else: win_amount = bet * 10
        elif reel1 == reel2 or reel2 == reel3 or reel1 == reel3:
            win_amount = int(bet * 1.5)

        if win_amount > 0:
            EconomyService.update_user_assets(session['user']['name'], win_amount, f"슬롯머신 당첨 ({reel1}{reel2}{reel3})")

        return render_template('games/slots_result.html', reels=[reel1, reel2, reel3], win=win_amount)
    return render_template('games/slots.html')

@games_bp.route('/horse_racing', methods=['GET', 'POST'])
def horse_racing():
    if request.method == 'POST':
        bet = int(request.form.get('bet'))
        chosen_horse = request.form.get('horse')

        success, msg = EconomyService.update_user_assets(session['user']['name'], -bet, "경마 베팅")
        if not success:
            flash(msg)
            return redirect(url_for('games.horse_racing'))

        winning_horse = str(random.randint(1, 4))

        if chosen_horse == winning_horse:
            EconomyService.update_user_assets(session['user']['name'], bet * 4, "경마 우승 배당금")
            flash(f"축하합니다! {winning_horse}번 마가 우승하여 {bet * 4} {CSVManager.get_config('currency_name')}을 획득했습니다!")
        else:
            flash(f"아쉽습니다. {winning_horse}번 마가 우승했습니다.")

    return render_template('games/horse.html')

@games_bp.route('/lottery', methods=['GET', 'POST'])
def lottery():
    if request.method == 'POST':
        price = int(CSVManager.get_config('lottery_price') or 50000)
        success, msg = EconomyService.update_user_assets(session['user']['name'], -price, "복권 구매")
        if not success:
            flash(msg)
            return redirect(url_for('games.lottery'))

        numbers = sorted(random.sample(range(1, 46), 6))
        ticket = {
            'user': session['user']['name'],
            'numbers': ','.join(map(str, numbers)),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'pending'
        }
        CSVManager.append('data/lottery.csv', ticket, ['user', 'numbers', 'timestamp', 'status'])
        flash(f"복권 구매 완료: {numbers}")

    tickets = CSVManager.read('data/lottery.csv')
    my_tickets = [t for t in tickets if t['user'] == session['user']['name']]
    return render_template('games/lottery.html', tickets=my_tickets)

@games_bp.route('/hilo', methods=['GET', 'POST'])
def hilo():
    if request.method == 'POST':
        bet = int(request.form.get('bet'))
        guess = request.form.get('guess') # higher, lower
        current_card = int(request.form.get('current_card'))

        success, msg = EconomyService.update_user_assets(session['user']['name'], -bet, "하이로우 베팅")
        if not success:
            flash(msg)
            return redirect(url_for('games.hilo'))

        next_card = random.randint(1, 13)
        while next_card == current_card:
            next_card = random.randint(1, 13)

        win = False
        if guess == 'higher' and next_card > current_card: win = True
        if guess == 'lower' and next_card < current_card: win = True

        if win:
            EconomyService.update_user_assets(session['user']['name'], bet * 2, "하이로우 승리")
            flash(f"성공! 다음 카드는 {next_card}였습니다. {bet*2} 획득!")
        else:
            flash(f"실패... 다음 카드는 {next_card}였습니다.")

    return render_template('games/hilo.html', card=random.randint(1, 13))

@games_bp.route('/roulette', methods=['GET', 'POST'])
def roulette():
    if request.method == 'POST':
        bet = int(request.form.get('bet'))
        target = request.form.get('target') # red, black, even, odd, or number

        success, msg = EconomyService.update_user_assets(session['user']['name'], -bet, "룰렛 베팅")
        if not success:
            flash(msg)
            return redirect(url_for('games.roulette'))

        result_num = random.randint(0, 36)
        red_nums = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]

        win = False
        multiplier = 0

        if target == 'red' and result_num in red_nums:
            win = True; multiplier = 2
        elif target == 'black' and result_num != 0 and result_num not in red_nums:
            win = True; multiplier = 2
        elif target == 'even' and result_num != 0 and result_num % 2 == 0:
            win = True; multiplier = 2
        elif target == 'odd' and result_num % 2 != 0:
            win = True; multiplier = 2
        elif target.isdigit() and int(target) == result_num:
            win = True; multiplier = 36

        if win:
            EconomyService.update_user_assets(session['user']['name'], bet * multiplier, "룰렛 승리")
            flash(f"결과: {result_num}! {multiplier}배 당첨! ({bet * multiplier} 획득)")
        else:
            flash(f"결과: {result_num}. 아쉽게 빗나갔습니다.")

    return render_template('games/roulette.html')

@games_bp.route('/blackjack', methods=['GET', 'POST'])
def blackjack():
    if request.method == 'POST':
        bet = int(request.form.get('bet', 0))
        action = request.form.get('action') # start, hit, stand

        if action == 'start':
            success, msg = EconomyService.update_user_assets(session['user']['name'], -bet, "블랙잭 베팅")
            if not success:
                flash(msg)
                return redirect(url_for('games.blackjack'))

            # Initial Deal
            deck = [2,3,4,5,6,7,8,9,10,10,10,10,11] * 4
            random.shuffle(deck)
            player_hand = [deck.pop(), deck.pop()]
            dealer_hand = [deck.pop(), deck.pop()]

            session['bj_deck'] = deck
            session['bj_player'] = player_hand
            session['bj_dealer'] = dealer_hand
            session['bj_bet'] = bet

        elif action == 'hit':
            deck = session.get('bj_deck')
            player_hand = session.get('bj_player')
            player_hand.append(deck.pop())
            session['bj_player'] = player_hand
            session['bj_deck'] = deck

            if sum(player_hand) > 21:
                flash("버스트! 패배했습니다.")
                return render_template('games/blackjack.html', player=player_hand, dealer=session['bj_dealer'], status='bust')

        elif action == 'stand':
            deck = session.get('bj_deck')
            dealer_hand = session.get('bj_dealer')
            player_hand = session.get('bj_player')

            while sum(dealer_hand) < 17:
                dealer_hand.append(deck.pop())

            player_score = sum(player_hand)
            dealer_score = sum(dealer_hand)

            result = ""
            if dealer_score > 21 or player_score > dealer_score:
                result = "win"
                EconomyService.update_user_assets(session['user']['name'], session['bj_bet'] * 2, "블랙잭 승리")
                flash(f"승리! (플레이어: {player_score}, 딜러: {dealer_score})")
            elif player_score == dealer_score:
                result = "draw"
                EconomyService.update_user_assets(session['user']['name'], session['bj_bet'], "블랙잭 무승부 반환")
                flash("무승부입니다.")
            else:
                result = "lose"
                flash(f"패배... (플레이어: {player_score}, 딜러: {dealer_score})")

            return render_template('games/blackjack.html', player=player_hand, dealer=dealer_hand, status=result)

        return render_template('games/blackjack.html', player=session.get('bj_player'), dealer=[session.get('bj_dealer')[0], '?'], status='ongoing')

    return render_template('games/blackjack.html')

@games_bp.route('/gacha', methods=['GET', 'POST'])
def gacha():
    if request.method == 'POST':
        cost = 5000
        success, msg = EconomyService.update_user_assets(session['user']['name'], -cost, "가챠 1회")
        if not success:
            flash(msg)
            return redirect(url_for('games.gacha'))

        # Probability logic
        rand = random.random() * 100
        if rand < 1: res = "SS등급 아이템"
        elif rand < 6: res = "S등급 아이템"
        elif rand < 21: res = "A등급 아이템"
        elif rand < 51: res = "B등급 아이템"
        else: res = "C등급 아이템"

        flash(f"뽑기 결과: {res}을(를) 획득했습니다!")
        # In a real app, save to inventory.csv
    return render_template('games/gacha.html')
