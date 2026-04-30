from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@bp.route('/portfolio')
@login_required
def portfolio():
    return render_template('portfolio.html')

@bp.route('/watchlist')
@login_required
def watchlist():
    return render_template('watchlist.html')

@bp.route('/invoices')
@login_required
def invoices():
    user_invoices = current_user.invoices
    return render_template('invoices.html', invoices=user_invoices)

@bp.route('/settings')
@login_required
def settings():
    return render_template('settings.html')
