from utils.csv_manager import CSVManager
from services.economy import EconomyService
from datetime import datetime

class ElectionService:
    @staticmethod
    def transition_phases():
        elections = CSVManager.read('data/elections.csv')
        updated = False
        now = datetime.now()

        for e in elections:
            if e['status'] == 'registration':
                # Check if registration period over (simplified: 1 week after start)
                start = datetime.strptime(e['start_date'], '%Y-%m-%d %H:%M:%S')
                if now > start + timedelta(weeks=1):
                    e['status'] = 'voting'
                    updated = True
            elif e['status'] == 'voting':
                end = datetime.strptime(e['end_date'], '%Y-%m-%d %H:%M:%S')
                if now > end:
                    e['status'] = 'completed'
                    ElectionService.finalize_election(e)
                    updated = True

        if updated:
            CSVManager.write('data/elections.csv', elections,
                             ['id', 'type', 'start_date', 'end_date', 'candidates', 'status', 'winner'])

    @staticmethod
    def finalize_election(election):
        # Count votes from a (yet to be created) votes.csv
        votes = CSVManager.read('data/votes.csv')
        counts = {}
        for v in votes:
            if v['election_id'] == election['id']:
                counts[v['candidate']] = counts.get(v['candidate'], 0) + 1

        if counts:
            winner = max(counts, key=counts.get)
            election['winner'] = winner
            # Update user grade
            users = CSVManager.read('data/users.csv')
            for u in users:
                if u['grade'] == '대통령급':
                    u['grade'] = '국민 1등급' # Previous president steps down
                if u['name'] == winner:
                    u['grade'] = '대통령급'
            CSVManager.write('data/users.csv', users, ['name', 'password', 'birth', 'grade', 'phone', 'resident_id', 'school_info', 'assets', 'status', 'credit_score'])

ElectionService.transition_phases() # Fixed import issue in app.py if needed
