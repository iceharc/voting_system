from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from datetime import datetime
from werkzeug.security import generate_password_hash
from functools import wraps
from sqlalchemy import func

from models import db, User, Candidate, Vote, Poll

admin_bp = Blueprint('admin', __name__)

# --------------------------
# Helper Decorators
# --------------------------
def admin_required(f):
    """Ensure the current user is an admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in first.", "warning")
            return redirect(url_for('auth.login'))
        if current_user.role != 'admin':
            flash("Admin access required.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


# --------------------------
# Admin Dashboard
# --------------------------
@admin_bp.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    users = User.query.filter_by(role='user').all()
    candidates = Candidate.query.all()
    votes = Vote.query.all()
    polls = Poll.query.order_by(Poll.start_time.desc()).all()

    current_time = datetime.utcnow()
    expired_polls = Poll.query.filter(Poll.end_time < current_time).all()

    expired_with_winners = []
    for poll in expired_polls:
        winner = poll.get_winner()
        expired_with_winners.append({'poll': poll, 'winner': winner})

    stats = (
        db.session.query(Candidate.name, db.func.count(Vote.candidate_id))
        .join(Vote, Candidate.id == Vote.candidate_id, isouter=True)
        .group_by(Candidate.id)
        .all()
    )

    return render_template(
        'admin_dashboard.html',
        users=users,
        candidates=candidates,
        votes=votes,
        polls=polls,
        stats=stats,
        expired_with_winners=expired_with_winners
    )


# --------------------------
# Add User
# --------------------------
@admin_bp.route('/admin/add_user', methods=['POST'])
@login_required
@admin_required
def add_user():
    username = request.form['username']
    password = request.form['password']
    hashed_password = generate_password_hash(password)

    new_user = User(username=username, password=hashed_password, role='user')
    db.session.add(new_user)
    db.session.commit()
    flash("User added successfully!", "success")
    return redirect(url_for('admin.admin_dashboard'))


# --------------------------
# Delete User (AJAX)
# --------------------------
@admin_bp.route('/admin/delete_user/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(id):
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User deleted successfully!"})


# --------------------------
# Add Poll
# --------------------------
@admin_bp.route('/admin/add_poll', methods=['POST'])
@login_required
@admin_required
def add_poll():
    try:
        title = request.form.get('title')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')

        if not title or not start_time or not end_time:
            flash("All fields are required.", "danger")
            return redirect(url_for('admin.admin_dashboard'))

        start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
        end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')

        new_poll = Poll(
            title=title,
            start_time=start_time,
            end_time=end_time,
            is_active=True
        )

        db.session.add(new_poll)
        db.session.commit()
        flash("Poll created successfully and is now active!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error creating poll: {e}", "danger")

    return redirect(url_for('admin.admin_dashboard'))


# --------------------------
# Add Candidate (Linked to Poll)
# --------------------------
@admin_bp.route('/admin/add_candidate', methods=['POST'])
@login_required
@admin_required
def add_candidate():
    name = request.form.get('name')
    poll_id = request.form.get('poll_id')

    if not name or not poll_id:
        flash("Candidate name and poll are required!", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    poll = Poll.query.get(poll_id)
    if not poll:
        flash("Selected poll does not exist.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    new_candidate = Candidate(name=name, poll_id=poll.id)
    db.session.add(new_candidate)
    db.session.commit()
    flash(f"Candidate '{name}' added successfully to poll '{poll.title}'!", "success")
    return redirect(url_for('admin.admin_dashboard'))


# --------------------------
# Poll Stats (JSON)
# --------------------------
@admin_bp.route('/admin/poll_stats/<int:poll_id>', methods=['GET'])
@login_required
@admin_required
def poll_stats(poll_id):
    poll = Poll.query.get(poll_id)
    if not poll:
        return jsonify({"error": "Poll not found"}), 404

    stats = []
    for candidate in poll.candidates:
        count = Vote.query.filter_by(candidate_id=candidate.id, poll_id=poll_id).count()
        stats.append([candidate.name, count])

    if stats:
        max_votes = max(v[1] for v in stats)
        winners = [v[0] for v in stats if v[1] == max_votes]
        winner_text = ", ".join(winners)
    else:
        winner_text = "No votes yet"

    return jsonify({
        "poll_id": poll.id,
        "poll_title": poll.title,
        "stats": stats,
        "winner": winner_text
    })


# --------------------------
# View Results (All Polls)
# --------------------------
@admin_bp.route('/admin/results')
@login_required
@admin_required
def results():
    polls = Poll.query.all()
    poll_results = []

    for poll in polls:
        results = (
            db.session.query(Candidate.name, func.count(Vote.id).label('votes'))
            .join(Vote, Candidate.id == Vote.candidate_id, isouter=True)
            .filter(Candidate.poll_id == poll.id)
            .group_by(Candidate.id)
            .order_by(db.desc('votes'))
            .all()
        )

        winner = poll.get_winner()
        poll_results.append({
            'poll': poll,
            'results': results,
            'winner': winner
        })

    return render_template('all_results.html', poll_results=poll_results,now=datetime.now)


# --------------------------
# View Results (Single Poll)
# --------------------------


# --------------------------
# Start / Stop / Delete Poll
# --------------------------
@admin_bp.route('/admin/start_poll/<int:poll_id>', methods=['POST'])
@login_required
@admin_required
def start_poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    poll.is_active = True
    poll.start_time = datetime.utcnow()
    db.session.commit()
    return jsonify({"message": "Poll started successfully"}), 200


@admin_bp.route('/admin/stop_poll/<int:poll_id>', methods=['POST'])
@login_required
@admin_required
def stop_poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    poll.is_active = False
    poll.end_time = datetime.utcnow()
    db.session.commit()
    return jsonify({"message": "Poll stopped successfully"}), 200


@admin_bp.route('/admin/delete_poll/<int:poll_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_poll(poll_id):
    try:
        poll = Poll.query.get_or_404(poll_id)
        db.session.delete(poll)
        db.session.commit()
        return jsonify({"message": "Poll deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# --------------------------
# Add Poll with Candidates
# --------------------------
@admin_bp.route('/admin/add_poll_with_candidates', methods=['POST'])
@login_required
@admin_required
def add_poll_with_candidates():
    try:
        title = request.form.get('title')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')

        if not title or not start_time or not end_time:
            flash("Please fill out all required fields.", "danger")
            return redirect(url_for('admin.admin_dashboard'))

        start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
        end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')

        new_poll = Poll(title=title, start_time=start_time, end_time=end_time, is_active=True)
        db.session.add(new_poll)
        db.session.commit()

        candidate_names = [v for k, v in request.form.items() if k.startswith('candidate_')]
        for name in candidate_names:
            if name.strip():
                candidate = Candidate(name=name.strip(), poll_id=new_poll.id)
                db.session.add(candidate)

        db.session.commit()
        flash(f"Poll '{title}' created with {len(candidate_names)} candidates!", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error creating poll with candidates: {e}", "danger")

    return redirect(url_for('admin.admin_dashboard'))




# --------------------------
# Update User (AJAX)
# --------------------------
@admin_bp.route('/admin/update_user/<int:id>', methods=['PUT'])
@login_required
@admin_required
def update_user(id):
    user = User.query.get_or_404(id)
    data = request.get_json()

    user.username = data.get('username', user.username)
    user.role = data.get('role', user.role)

    if data.get('password'):
        user.password = generate_password_hash(data['password'])

    db.session.commit()
    return jsonify({"message": "User updated successfully!"}), 200
