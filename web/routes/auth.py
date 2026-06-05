from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from web.models import db, User
from oauthlib.oauth2 import WebApplicationClient
import requests
import json
from web.config import Config

bp = Blueprint('auth', __name__, url_prefix='/auth')

client = WebApplicationClient(Config.GOOGLE_CLIENT_ID) if Config.GOOGLE_CLIENT_ID else None

def get_google_provider_cfg():
    return requests.get(Config.GOOGLE_DISCOVERY_URL).json()

@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        full_name = request.form.get('full_name')
        password = request.form.get('password')
        
        if not email or not password or not full_name:
            flash('All fields are required', 'error')
            return render_template('auth/signup.html')
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered', 'error')
            return render_template('auth/signup.html')
        
        user = User(email=email, full_name=full_name)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        flash('Account created successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('auth/signup.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Email and password are required', 'error')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            flash('Invalid email or password', 'error')
            return render_template('auth/login.html')
        
        login_user(user)
        next_page = request.args.get('next')
        return redirect(next_page or url_for('main.dashboard'))
    
    return render_template('auth/login.html')

@bp.route('/google')
def google_login():
    if not client:
        flash('Google OAuth is not configured', 'error')
        return redirect(url_for('auth.login'))
    
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]
    
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=Config.REDIRECT_URI,
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)

@bp.route('/callback')
def callback():
    if not client:
        flash('Google OAuth is not configured', 'error')
        return redirect(url_for('auth.login'))
    
    code = request.args.get("code")
    
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]
    
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(Config.GOOGLE_CLIENT_ID, Config.GOOGLE_CLIENT_SECRET),
    )
    
    client.parse_request_body_response(json.dumps(token_response.json()))
    
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)
    
    if userinfo_response.json().get("email_verified"):
        google_id = userinfo_response.json()["sub"]
        email = userinfo_response.json()["email"]
        full_name = userinfo_response.json().get("name")
        picture = userinfo_response.json().get("picture")
    else:
        flash('User email not verified by Google', 'error')
        return redirect(url_for('auth.login'))
    
    user = User.query.filter_by(google_id=google_id).first()
    
    if not user:
        user = User.query.filter_by(email=email).first()
        if user:
            user.google_id = google_id
            user.profile_picture = picture
        else:
            user = User(
                email=email,
                full_name=full_name,
                google_id=google_id,
                profile_picture=picture
            )
            db.session.add(user)
        
        db.session.commit()
    
    login_user(user)
    return redirect(url_for('main.dashboard'))

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'success')
    return redirect(url_for('main.index'))
