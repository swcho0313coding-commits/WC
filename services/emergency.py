from utils.csv_manager import CSVManager
from datetime import datetime

class EmergencyService:
    @staticmethod
    def is_emergency():
        records = CSVManager.read('data/emergency_records.csv')
        for r in records:
            if r['status'] == 'active':
                return True, r['type']
        return False, None

    @staticmethod
    def get_system_grade(username):
        # If emergency is active, map system grade to military rank
        is_em, em_type = EmergencyService.is_emergency()
        users = CSVManager.read('data/users.csv')
        user = next((u for u in users if u['name'] == username), None)
        if not user: return None

        if is_em and em_type == 'martial_law':
            mapping = CSVManager.read('data/military_mapping.csv')
            for m in mapping:
                if user['grade'] in m['system_grades'].split(','):
                    return m['military_rank']
        return user['grade']
