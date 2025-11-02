from flask import Blueprint, render_template, request, redirect, url_for, flash, render_template_string,jsonify
from flask_login import login_required, current_user
from models import db, Vote, Candidate, VotingSession, Poll
from datetime import datetime

user_bp = Blueprint('user', __name__)

# --------------------------
# User Dashboard
# --------------------------
@user_bp.route('/user/dashboard')


def user_dashboard():
    if current_user.role == 'admin':
        flash("Admins should use the admin dashboard.", "info")
        return redirect(url_for('admin.admin_dashboard'))
    
    if current_user.role != 'user':
        flash("Access denied. Invalid role.", "danger")
        return redirect(url_for('auth.login'))

    current_time = datetime.utcnow()

    # Active polls (still open)
    active_polls = Poll.query.filter(Poll.end_time >= current_time).order_by(Poll.start_time.desc()).all()

    # Expired polls (closed)
    expired_polls = Poll.query.filter(Poll.end_time < current_time).order_by(Poll.end_time.desc()).all()

    # User’s votes
    # User’s votes (both poll and candidate)
    user_votes_query = Vote.query.filter_by(user_id=current_user.id).all()

    user_votes = {vote.poll_id: vote.candidate_id for vote in user_votes_query}
    user_voted_poll_ids = list(user_votes.keys())

    # Build list of winners for expired polls
    expired_with_winners = []
    for poll in expired_polls:
        winner = poll.get_winner()
        expired_with_winners.append({
            'poll': poll,
            'winner': winner
        })

    return render_template(
        'user_dashboard.html',
        active_polls=active_polls,
        expired_with_winners=expired_with_winners,
        user_voted_poll_ids=user_voted_poll_ids,
        user_votes=user_votes
    )

# --------------------------
# Voting Logic (Updated)
# --------------------------
@user_bp.route('/vote', methods=['POST'])

def vote():
    # ✅ Proper authorization check
    if current_user.role != 'user':
        flash("Only registered users can vote!", "danger")
        return redirect(url_for('user.user_dashboard'))

    candidate_id = request.form.get('candidate_id')
    poll_id = request.form.get('poll_id')

    # ✅ Validate input
    if not candidate_id or not poll_id:
        flash("Invalid vote request. Please try again.", "warning")
        return redirect(url_for('user.user_dashboard'))

    # ✅ Verify poll exists
    poll = Poll.query.get(poll_id)
    if not poll:
        flash("Poll not found.", "danger")
        return redirect(url_for('user.user_dashboard'))

    # ✅ Verify candidate exists and belongs to this poll
    candidate = Candidate.query.get(candidate_id)
    if not candidate or candidate.poll_id != int(poll_id):
        flash("Invalid candidate selection.", "danger")
        return redirect(url_for('user.user_dashboard'))

    # ✅ Check if voting period is open
    current_time = datetime.utcnow()
    if poll.start_time > current_time:
        flash("Voting for this poll has not started yet.", "warning")
        return redirect(url_for('user.user_dashboard'))
    
    if poll.end_time < current_time:
        flash("Voting session for this poll has ended.", "danger")
        return redirect(url_for('user.user_dashboard'))

    # ✅ Check if the user already voted in this poll
    existing_vote = Vote.query.filter_by(user_id=current_user.id, poll_id=poll_id).first()
    if existing_vote:
        flash("You have already voted in this poll.", "warning")
        return redirect(url_for('user.user_dashboard'))

    # ✅ Save vote to the database
    try:
        new_vote = Vote(
            user_id=current_user.id,
            candidate_id=candidate_id,
            poll_id=poll_id,
            timestamp=datetime.utcnow()  # Add timestamp if your model supports it
        )
        db.session.add(new_vote)
        
        # ✅ Update user's has_voted flag if needed
        if not current_user.has_voted:
            current_user.has_voted = True
        
        db.session.commit()
        flash("✅ Your vote has been successfully submitted!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred while submitting your vote. Please try again.", "danger")
        print(f"Vote error: {e}")  # Log for debugging
    
    return redirect(url_for('user.user_dashboard'))


# --------------------------
# Active Polls Route
# --------------------------
@user_bp.route('/user/get_polls')
@login_required
def get_polls():
   
    
    current_time = datetime.utcnow()
    polls = (
        Poll.query
        .filter(
            Poll.end_time > current_time,     # exclude expired polls
            Poll.is_active == True            # ensure poll is active
        )
        .order_by(Poll.start_time.desc())
        .all()
    )
    polls = Poll.query.filter(Poll.end_time >= current_time).order_by(Poll.start_time.desc()).all()
    
    # ✅ Get user's voted poll IDs
    user_voted_poll_ids = [vote.poll_id for vote in Vote.query.filter_by(user_id=current_user.id).all()]

    return render_template_string('''
      {% for poll in polls %}
        <div class="col-md-6">
          <div class="poll-card shadow-sm">
            <div class="poll-title">
              <h5>{{ poll.title }}</h5>
              <small>{{ poll.start_time.strftime('%Y-%m-%d %H:%M') }} → {{ poll.end_time.strftime('%Y-%m-%d %H:%M') }}</small>
            </div>
            <div class="p-3">
              {% set candidates = poll.candidates %}
              {% if candidates %}
                {% set has_voted_in_poll = poll.id in user_voted_poll_ids %}
                {% for candidate in candidates %}
                  <div class="d-flex justify-content-between align-items-center border-bottom py-2">
                    <span>{{ candidate.name }}</span>
                    {% if not has_voted_in_poll %}
                      <form action="{{ url_for('user.vote') }}" method="POST" class="d-inline">
                        <input type="hidden" name="candidate_id" value="{{ candidate.id }}">
                        <input type="hidden" name="poll_id" value="{{ poll.id }}">
                        <button type="submit" class="btn btn-outline-primary btn-sm">Vote</button>
                      </form>
                    {% else %}
                      <span class="text-success small">✓ Voted</span>
                    {% endif %}
                  </div>
                {% endfor %}
              {% else %}
                <p class="text-muted text-center">No candidates yet.</p>
              {% endif %}
            </div>
          </div>
        </div>
      {% else %}
        <p class="text-center text-muted">No active polls available.</p>
      {% endfor %}
    ''', polls=polls, user_voted_poll_ids=user_voted_poll_ids)


# --------------------------
# USER VOTE HANDLER
# --------------------------
@user_bp.route('/user/vote', methods=['POST'])

def user_vote():
    poll_id = request.form.get('poll_id')
    candidate_id = request.form.get('candidate_id')

    # Check if poll and candidate exist
    poll = Poll.query.get(poll_id)
    candidate = Candidate.query.get(candidate_id)

    if not poll or not candidate:
        flash("Invalid poll or candidate.", "danger")
        return redirect(url_for('user.user_home'))

    # Check if the user already voted in this poll
    existing_vote = Vote.query.filter_by(user_id=current_user.id, poll_id=poll_id).first()
    if existing_vote:
        flash("You have already voted in this poll!", "warning")
        return redirect(url_for('user.user_home'))

    # Record the vote
    new_vote = Vote(user_id=current_user.id, candidate_id=candidate_id, poll_id=poll_id)
    db.session.add(new_vote)
    db.session.commit()

    flash("Your vote has been recorded successfully!", "success")
    return redirect(url_for('user.user_dashboard'))



