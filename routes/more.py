from flask import Blueprint, render_template, session
from utils.auth import login_required

more_bp = Blueprint('more', __name__)

@more_bp.route('/')
@login_required
def index():
    return render_template('more/index.html')

@more_bp.route('/qr_scan')
@login_required
def qr_scan():
    return render_template('more/qr_scan.html')
