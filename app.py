import os

from flask import Flask, render_template, request, flash, redirect, session, g, abort
from flask_debugtoolbar import DebugToolbarExtension
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError
from flask_sqlalchemy import SQLAlchemy


from models import db, connect_db, User, Stock_holding, Transaction
import functions as f
import queries as q
login_required = f.login_required


app = Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgresql:///salomon_financial'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")

toolbar = DebugToolbarExtension(app)



connect_db(app)

@app.route('/')
def home_page():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register user"""
    session.clear()
    if request.method == 'POST':
        username, password, confirmation = (
                request.form.get('username'),
                request.form.get('password'),
                request.form.get('confirmation')
            )

        if not username:
            return f.error_msg("Missing username")
        elif not password:
            return f.error_msg("Missing password")
        elif not confirmation:
            return f.error_msg("Missing confirmation")
        elif password != confirmation:
            return f.error_msg("Password doesn't match confirmation")

        hashed_pwd = Bcrypt.generate_password_hash(password).decode('UTF-8')

        try:
            q.insert_user(username, hashed_pwd)
        except Exception:
            return f.error_msg("Username already exists")

        session['user_id'] = q.select_user_by_username(username).id

        return redirect('/')

    return render_template("register.html")


@app.route('/login', methods=['GET','POST'])
def login():
    """Log user in"""
    session.clear()

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username: return f.error_msg("Must provide username")
        elif not password: return f.error_msg("Must provide password")

        user = q.select_user_by_username(username)
        try:
            if Bcrypt.check_password_hash(user.hashed_pwd, password):
                session['user_id'] = user.id
                return redirect('/')
            else:
                return f.error_msg("Incorrect password")
        except AttributeError:
            return f.error_msg("No such user")
    else:
        return render_template("login.html")

@app.route('/logout')
def logout_user():
    session.pop('user_id')
    flash("Goodbye!", "info")
    return redirect('/')


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Show user profile information"""
    if request.method == 'POST':
        password = request.form.get('password')
        new_password = request.form.get('new')
        confirmation = request.form.get('confirmation')
        if not password or not new_password or not confirmation:
            return f.error_msg("Please fill all fields")
        elif new_password != confirmation:
            return f.error_msg("New password and confirmation don't match")

        user = q.select_user_by_id(session['user_id'])
        if Bcrypt.check_password_hash(user.hashed_pwd, password):
            new_hash = Bcrypt.generate_password_hash(new_password).decode('UTF-8')
            q.update_user_hash(new_hash, session['user_id'])
            return redirect('/login')
        else:
            return f.error_msg("Incorrect password")
    else:
        user = q.select_user_by_id(session['user_id'])
        user.cash = f.usd(user.cash)
        return render_template('profile.html', user=user)

@app.route('/quote', methods=['GET', 'POST'])
@login_required
def quote():
    """Get stock quote"""
    if request.method == 'POST':
        quote = f.lookup(request.form.get('symbol'))
        if not quote:
            return f.error_msg("Company doesn't exist.")
        return render_template(
                'quoted.html',
                symbol=quote['symbol'],
                price=quote['price'],
                name=quote['name'],
                )
    else:
        return render_template('quote.html', stocks=stocks)

@app.route('/sell', methods=['GET', 'POST'])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == 'POST':
        symbol = request.form.get('symbol')
        shares = request.form.get('shares')
        if not symbol:
            return f.error_msg("Provide a symbol")
        elif not shares or not shares.isdigit():
            return f.error_msg("Provide a valid quantity")
        shares = float(shares)
        quote = f.lookup(symbol)
        if not quote:
            return f.error_msg("No such company")
        try:
            stock = q.select_stock_by_symbol(symbol)
            position = q.select_transactions_by_stock(
                    stock.id,
                    session['user_id'])
            if position.shares >= shares:
                order_total = shares * quote['price']
                q.insert_transaction(
                        session['user_id'],
                        stock.id,
                        shares*-1,
                        quote['price'])
                q.update_user_cash(order_total, session['user_id'])
                return redirect('/')
            else:
                return f.error_msg("You don't own enough of that stock.")
        except AttributeError:
            return f.error_msg("You don't own that stock")
    else:
        user = q.select_user_by_id(session['user_id'])
        return render_template('sell.html',
                portfolio=f.build_portfolio(
                    q.select_stocks_by_user(user.id),
                    user.cash)
                )

@app.route('/history')
@login_required
def history():
    """Show history of transactions"""
    history = dict(sorted(
        f.build_history(
            q.select_transactions_by_user(
                session['user_id']
            )).items()
        ))
    return render_template('history.html', history=history)
###################################################################################################################################################################################################

@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response