from app import db
from models import Poll

polls = Poll.query.all()
for poll in polls:
    print(f"ID: {poll.id}")
    print(f"Title: {poll.title}")
    print(f"Start Time: {poll.start_time}")
    print(f"End Time: {poll.end_time}")
    print(f"Active: {poll.is_active}")
    print("-----")
