from utils.csv_manager import CSVManager
from datetime import datetime, timedelta
import uuid

class ElectionService:
    @staticmethod
    def start_new_election():
        election_id = str(uuid.uuid4())
        start_date = datetime.now()
        new_election = {
            'id': election_id,
            'type': 'presidential',
            'start_date': start_date.strftime('%Y-%m-%d %H:%M:%S'),
            'end_date': (start_date + timedelta(weeks=3)).strftime('%Y-%m-%d %H:%M:%S'),
            'candidates': '',
            'status': 'registration',
            'winner': ''
        }
        CSVManager.append('data/elections.csv', new_election,
                          ['id', 'type', 'start_date', 'end_date', 'candidates', 'status', 'winner'])
        # Broadcast notice via socket or CSV notice
        return election_id

    @staticmethod
    def transition_phases():
        elections = CSVManager.read('data/elections.csv')
        updated = False
        now = datetime.now()

        for e in elections:
            if e['status'] == 'completed': continue

            start = datetime.strptime(e['start_date'], '%Y-%m-%d %H:%M:%S')

            # D-21 to D-4: Registration
            # D-4 to D-1: Campaign (Candidate closing)
            # D-0: Voting

            if e['status'] == 'registration':
                if now >= start + timedelta(days=17): # D-4
                    e['status'] = 'campaign'
                    updated = True
            elif e['status'] == 'campaign':
                if now >= start + timedelta(days=21): # D-0
                    e['status'] = 'voting'
                    updated = True
            elif e['status'] == 'voting':
                if now >= start + timedelta(days=22): # After 24h
                    e['status'] = 'completed'
                    ElectionService.finalize_results(e)
                    updated = True

        if updated:
            CSVManager.write('data/elections.csv', elections,
                             ['id', 'type', 'start_date', 'end_date', 'candidates', 'status', 'winner'])

    @staticmethod
    def finalize_results(election):
        votes = CSVManager.read('data/votes.csv')
        counts = {}
        candidates = election['candidates'].split(',') if election['candidates'] else []
        for c in candidates: counts[c] = 0

        for v in votes:
            if v['election_id'] == election['id']:
                counts[v['candidate']] = counts.get(v['candidate'], 0) + 1

        if counts:
            winner = max(counts, key=counts.get)
            election['winner'] = winner

            # Role swap
            users = CSVManager.read('data/users.csv')
            for u in users:
                if u['grade'] == '대통령급':
                    u['grade'] = '국민 1등급' # Simplified demotion
                if u['name'] == winner:
                    u['grade'] = '대통령급'

            CSVManager.write('data/users.csv', users, ['name', 'password', 'birth', 'grade', 'phone', 'resident_id', 'school_info', 'assets', 'status', 'credit_score'])

            # Log history
            history = {
                'election_id': election['id'],
                'winner': winner,
                'total_votes': str(sum(counts.values())),
                'date': datetime.now().strftime('%Y-%m-%d')
            }
            CSVManager.append('data/election_history.csv', history, ['election_id', 'winner', 'total_votes', 'date'])
