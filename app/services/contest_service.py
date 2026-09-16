from datetime import datetime, timezone
import secrets
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional

from app.models.contest import Contest, ContestProblem, ContestParticipant
from app.models.problem import Problem
from app.models.user import User
from app.models.submission import Submission

class ContestService:
    @staticmethod
    def _contest_status(contest: Contest):
        now = datetime.now(timezone.utc)
        start = contest.starts_at.replace(tzinfo=timezone.utc) if contest.starts_at.tzinfo is None else contest.starts_at
        end = contest.ends_at.replace(tzinfo=timezone.utc) if contest.ends_at.tzinfo is None else contest.ends_at
        if now < start: return "upcoming"
        if now > end: return "ended"
        return "active"

    @staticmethod
    def create_contest(db: Session, payload, current_user_id: int):
        starts = payload.starts_at.replace(tzinfo=timezone.utc) if payload.starts_at.tzinfo is None else payload.starts_at
        from datetime import timedelta
        ends = starts + timedelta(minutes=payload.duration_minutes)
        
        contest = Contest(
            title=payload.title,
            description=payload.description,
            invite_code=secrets.token_urlsafe(8),
            created_by=current_user_id,
            duration_minutes=payload.duration_minutes,
            starts_at=starts,
            ends_at=ends,
            is_public=payload.is_public,
        )
        db.add(contest)
        db.flush()

        for i, pid in enumerate(payload.problem_ids):
            points = payload.points_per_problem[i] if payload.points_per_problem and i < len(payload.points_per_problem) else 100
            db.add(ContestProblem(contest_id=contest.id, problem_id=pid, points=points))

        db.add(ContestParticipant(contest_id=contest.id, user_id=current_user_id))
        db.commit()
        db.refresh(contest)
        
        return contest

    @staticmethod
    def list_contests(db: Session, user_id: int):
        joined_ids = {p.contest_id for p in db.query(ContestParticipant).filter(
            ContestParticipant.user_id == user_id).all()}
        all_contests = db.query(Contest).all()
        result = []
        for c in all_contests:
            result.append({
                "id": c.id,
                "title": c.title,
                "invite_code": c.invite_code,
                "duration_minutes": c.duration_minutes,
                "starts_at": c.starts_at,
                "ends_at": c.ends_at,
                "status": ContestService._contest_status(c),
                "is_mine": c.created_by == user_id,
                "is_joined": c.id in joined_ids,
            })
        result.sort(key=lambda x: x["starts_at"], reverse=True)
        return result

    @staticmethod
    def join_contest(db: Session, contest: Contest, user_id: int):
        existing = db.query(ContestParticipant).filter(
            ContestParticipant.contest_id == contest.id,
            ContestParticipant.user_id == user_id
        ).first()
        if not existing:
            db.add(ContestParticipant(contest_id=contest.id, user_id=user_id))
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
        return {"message": "Joined successfully", "contest_id": contest.id}

    @staticmethod
    def get_contest_detail(db: Session, contest: Contest, user_id: int):
        problems = db.query(ContestProblem).filter(ContestProblem.contest_id == contest.id).all()
        problem_details = []
        for cp in problems:
            p = db.query(Problem).filter(Problem.id == cp.problem_id).first()
            if p:
                problem_details.append({
                    "id": p.id, "title": p.title,
                    "difficulty": p.difficulty, "points": cp.points
                })
        
        participants = db.query(ContestParticipant).filter(
            ContestParticipant.contest_id == contest.id).count()

        is_joined = db.query(ContestParticipant).filter(
            ContestParticipant.contest_id == contest.id,
            ContestParticipant.user_id == user_id).first() is not None

        return {
            "id": contest.id,
            "title": contest.title,
            "description": contest.description,
            "invite_code": contest.invite_code,
            "duration_minutes": contest.duration_minutes,
            "starts_at": contest.starts_at,
            "ends_at": contest.ends_at,
            "status": ContestService._contest_status(contest),
            "problems": problem_details,
            "participants": participants,
            "is_joined": is_joined,
            "is_mine": contest.created_by == user_id,
            "leaderboard": ContestService.build_leaderboard(db, contest),
        }

    @staticmethod
    def build_leaderboard(db: Session, contest: Contest):
        participants = db.query(ContestParticipant).filter(
            ContestParticipant.contest_id == contest.id).all()
        contest_problems = db.query(ContestProblem).filter(
            ContestProblem.contest_id == contest.id).all()

        starts = contest.starts_at.replace(tzinfo=timezone.utc) if contest.starts_at.tzinfo is None else contest.starts_at
        ends = contest.ends_at.replace(tzinfo=timezone.utc) if contest.ends_at.tzinfo is None else contest.ends_at

        participant_user_ids = [p.user_id for p in participants]
        problem_ids = [cp.problem_id for cp in contest_problems]

        users = db.query(User).filter(User.id.in_(participant_user_ids)).all()
        user_dict = {u.id: u for u in users}

        all_subs = []
        if participant_user_ids and problem_ids:
            all_subs = db.query(Submission).filter(
                Submission.user_id.in_(participant_user_ids),
                Submission.problem_id.in_(problem_ids),
                Submission.created_at >= starts,
                Submission.created_at <= ends,
                Submission.is_sample_only == False
            ).order_by(Submission.created_at.asc()).all()

        from collections import defaultdict
        user_prob_subs = defaultdict(lambda: defaultdict(list))
        for sub in all_subs:
            user_prob_subs[sub.user_id][sub.problem_id].append(sub)

        leaderboard = []
        for p in participants:
            user = user_dict.get(p.user_id)
            if not user:
                continue
            total_points = 0
            solved = 0
            penalty = 0
            problem_status = {}

            for cp in contest_problems:
                subs = user_prob_subs[p.user_id][cp.problem_id]
                wrong = 0
                accepted_at = None
                for s in subs:
                    if s.verdict == 'accepted':
                        accepted_at = s.created_at
                        break
                    else:
                        wrong += 1
                
                if accepted_at:
                    elapsed = int((accepted_at.replace(tzinfo=timezone.utc) - starts).total_seconds()) // 60
                    total_points += cp.points
                    penalty += elapsed + wrong * 20
                    solved += 1
                    problem_status[cp.problem_id] = {"status": "accepted", "attempts": wrong + 1, "time": elapsed}
                elif wrong > 0:
                    problem_status[cp.problem_id] = {"status": "wrong", "attempts": wrong}
                else:
                    problem_status[cp.problem_id] = {"status": "none", "attempts": 0}

            leaderboard.append({
                "user_id": p.user_id,
                "username": user.username,
                "points": total_points,
                "solved": solved,
                "penalty": penalty,
                "problem_status": problem_status,
            })

        leaderboard.sort(key=lambda x: (-x["points"], x["penalty"]))
        for i, row in enumerate(leaderboard):
            row["rank"] = i + 1

        return leaderboard
