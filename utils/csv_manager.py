import csv
import threading
import os

class CSVManager:
    _lock = threading.Lock()

    @staticmethod
    def read(filepath):
        if not os.path.exists(filepath):
            return []
        with CSVManager._lock:
            with open(filepath, 'r', newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                return list(reader)

    @staticmethod
    def write(filepath, data, headers):
        with CSVManager._lock:
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(data)

    @staticmethod
    def append(filepath, row, headers):
        with CSVManager._lock:
            file_exists = os.path.exists(filepath)
            with open(filepath, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)

    @staticmethod
    def get_config(key):
        config = CSVManager.read('data/config.csv')
        for item in config:
            if item['key'] == key:
                return item['value']
        return None

    @staticmethod
    def log_activity(ip, user, action, status):
        from datetime import datetime
        row = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ip': ip,
            'user': user,
            'action': action,
            'status': status
        }
        CSVManager.append('data/logs/activity.csv', row, ['timestamp', 'ip', 'user', 'action', 'status'])
