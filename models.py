from datetime import datetime

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy


bcrypt = Bcrypt()
db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)
    cash = db.Column(db.Float, default=500000.00)
    transactions = db.relationship('Transaction', cascade='all,delete',
            backref='user')

    def __repr__(self):
        return f'<User {self.username}>'

    @classmethod
    def register(cls, username, pwd):
        """Register user w/hashed password & return user."""

        hashed = bcrypt.generate_password_hash(pwd)
        # turn bytestring into normal (unicode utf8) string
        hashed_utf8 = hashed.decode("utf8")

        # return instance of user w/username and hashed pwd
        return cls(username=username, password=hashed_utf8)

    @classmethod
    def authenticate(cls, username, pwd):
        """Validate that user exists & password is correct.

        Return user if valid; else return False.
        """

        u = User.query.filter_by(username=username).first()

        if u and bcrypt.check_password_hash(u.password, pwd):
            # return user instance
            return u
        else:
            return False


class Stock_holding(db.Model):
    __tablename__ = 'stock_holding'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    symbol = db.Column(db.String(20), unique=True, nullable=False)
    quantity=db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(80), unique=True, nullable=False)
    transactions = db.relationship('Transaction', cascade='all,delete',
            backref='stock')

    def __repr__(self):
        return f'<Stock {self.symbol}>'


class Transaction(db.Model):
    __tablename__ = 'transaction'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False)

    stock_id = db.Column(db.Integer,
        db.ForeignKey('stocks.id', ondelete='CASCADE'),
        nullable=False)

    quantity = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    type = db.Column(db.String, nullable=False)
    time = db.Column(db.DateTime, nullable=False,
        default=datetime.utcnow)

    def __repr__(self):
        return f'<Transaction {self.user}: {self.stock_holding}>'