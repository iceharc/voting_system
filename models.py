from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# ------------------------------
# Poll Model
# ------------------------------
# ------------------------------
# Poll Model
# ------------------------------
class Poll(db.Model):
    __tablename__ = 'poll'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    candidates = db.relationship('Candidate', backref='poll', lazy=True, cascade="all, delete")
    votes = db.relationship('Vote', back_populates='poll', lazy=True, cascade="all, delete")

    def is_open(self):
        """Check if the poll is currently active (by time)."""
        now = datetime.utcnow()
        return self.is_active and self.start_time <= now <= self.end_time

    def get_winner(self):
        """Return the candidate with the highest votes for this poll."""
        from sqlalchemy import func
        winner = (
            db.session.query(Candidate, func.count(Vote.id).label('vote_count'))
            .join(Vote, Candidate.id == Vote.candidate_id, isouter=True)
            .filter(Candidate.poll_id == self.id)
            .group_by(Candidate.id)
            .order_by(db.desc('vote_count'))
            .first()
        )
        if winner and winner[1] > 0:
            return {'name': winner[0].name, 'votes': winner[1]}
        return None


# ------------------------------
# User Model
# ------------------------------
class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # "admin" or "user"
    has_voted = db.Column(db.Boolean, default=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)

    # Relationship to votes
    votes = db.relationship('Vote', backref='user', lazy=True, cascade="all, delete")


# ------------------------------
# Candidate Model
# ------------------------------
class Candidate(db.Model):
    __tablename__ = 'candidate'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    poll_id = db.Column(db.Integer, db.ForeignKey('poll.id', ondelete='CASCADE'), nullable=False)

    # Relationship to votes
    votes = db.relationship('Vote', backref='candidate', lazy=True, cascade="all, delete")

# ------------------------------
# Vote Model
# ------------------------------
class Vote(db.Model):
    __tablename__ = 'vote'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id', ondelete='CASCADE'), nullable=False)
    poll_id = db.Column(db.Integer, db.ForeignKey('poll.id', ondelete='CASCADE'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship back to Poll
    poll = db.relationship('Poll', back_populates='votes')  # ✅ fixed — now matches Poll.votes

# ------------------------------
# Voting Session (Optional Global Control)
# ------------------------------
class VotingSession(db.Model):
    __tablename__ = 'voting_session'

    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=False)


def get_winner(self):
    """Return the candidate with the highest votes for this poll."""
    from sqlalchemy import func
    winner = (
        db.session.query(Candidate, func.count(Vote.id).label('vote_count'))
        .join(Vote, Candidate.id == Vote.candidate_id, isouter=True)
        .filter(Candidate.poll_id == self.id)
        .group_by(Candidate.id)
        .order_by(db.desc('vote_count'))
        .first()
    )
    if winner and winner[1] > 0:
        return {'name': winner[0].name, 'votes': winner[1]}
    return None
