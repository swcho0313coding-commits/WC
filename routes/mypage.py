from flask import Blueprint, render_template, session, redirect, url_for, flash
from utils.csv_manager import CSVManager
from utils.auth import login_required, get_user_by_name
import os

mypage_bp = Blueprint('mypage', __name__)

@mypage_bp.route('/')
@login_required
def index():
    user = session['user']
    # Refresh user data from CSV
    user = get_user_by_name(user['name'])
    session['user'] = user # Update session

    id_card_url = f"uploads/id_cards/{user['name']}_id.png"
    medals = CSVManager.read('data/medals.csv')
    user_medals = [m for m in medals if m['user'] == user['name']]
    return render_template('mypage/index.html', user=user, id_card_url=id_card_url, medals=user_medals)
