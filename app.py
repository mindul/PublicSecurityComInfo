from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
import scraper
import json
import os
from extensions import db, login_manager
from models import User
from flask_login import login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-this-in-prod'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Ensure instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



# Cache for company list to avoid re-scraping on every reload
# In a real app, this might be a database or Redis
COMPANY_LIST_CACHE = []

def get_companies():
    global COMPANY_LIST_CACHE
    if not COMPANY_LIST_CACHE:
        # Try to load from json if exists
        # Or scrape fresh
        print("Scraping company list...")
        # Scrape 4 pages as requested
        COMPANY_LIST_CACHE = scraper.fetch_company_list(max_pages=4)
    return COMPANY_LIST_CACHE

@app.route('/')
def landing():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return render_template('landing.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('비밀번호가 일치하지 않습니다.')
        else:
            user = User.query.filter_by(username=username).first()
            if user:
                flash('이미 존재하는 사용자명입니다.')
            else:
                new_user = User(username=username)
                new_user.set_password(password)
                db.session.add(new_user)
                db.session.commit()
                flash('회원가입 요청이 되었습니다. 관리자 승인 후 로그인해주세요.')
                return redirect(url_for('landing'))
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if not user.is_approved:
                flash('관리자 승인 대기 중입니다.')
            else:
                login_user(user)
                return redirect(url_for('home'))
        else:
            flash('아이디 또는 비밀번호가 올바르지 않습니다.')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('landing'))

@app.route('/home')
@login_required
def home():
    companies = get_companies()
    return render_template('home.html', companies=companies)

@app.route('/api/company/<publish_no>')
@login_required
def company_detail(publish_no):
    try:
        details = scraper.fetch_company_detail(publish_no)
        if details:
            return jsonify(details)
        else:
            return jsonify({'error': 'Details not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/home/fsiadmin')
def admin_dashboard():
    if not current_user.is_authenticated:
        return redirect(url_for('landing'))
    if not current_user.is_admin:
        return redirect(url_for('home'))
    
    users = User.query.filter_by(is_approved=False).all()
    return render_template('admin.html', users=users)

@app.route('/home/fsiadmin/approve/<int:user_id>')
@login_required
def approve_user(user_id):
    if not current_user.is_admin:
        return redirect(url_for('home'))
        
    user = User.query.get(user_id)
    if user:
        user.is_approved = True
        db.session.commit()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/home/fsiadmin/reject/<int:user_id>')
@login_required
def reject_user(user_id):
    if not current_user.is_admin:
        return redirect(url_for('home'))
        
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
    
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5050, host='0.0.0.0')
