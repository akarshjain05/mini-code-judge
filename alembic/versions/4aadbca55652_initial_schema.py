"""Initial schema

Revision ID: 4aadbca55652
Revises: 
Create Date: 2026-07-09 17:11:53.073721

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4aadbca55652'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables from scratch."""

    # ── users ──────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('username', sa.String(50), nullable=False),
        sa.Column('full_name', sa.String(100), nullable=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone_number', sa.String(30), nullable=True),
        sa.Column('password', sa.String(255), nullable=True),
        sa.Column('google_id', sa.String(255), nullable=True),
        sa.Column('github_id', sa.String(255), nullable=True),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('profile_picture', sa.Text(), nullable=True),
        sa.Column('date_of_birth', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_unique_constraint('uq_users_email', 'users', ['email'])
    op.create_unique_constraint('uq_users_google_id', 'users', ['google_id'])
    op.create_unique_constraint('uq_users_github_id', 'users', ['github_id'])
    op.create_index(op.f('ix_users_google_id'), 'users', ['google_id'], unique=False)
    op.create_index(op.f('ix_users_github_id'), 'users', ['github_id'], unique=False)

    # ── problems ───────────────────────────────────────────────────────
    op.create_table(
        'problems',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('difficulty', sa.String(10), server_default='easy'),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(op.f('ix_problems_id'), 'problems', ['id'], unique=False)

    # ── test_cases ─────────────────────────────────────────────────────
    op.create_table(
        'test_cases',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('problem_id', sa.Integer(), nullable=False),
        sa.Column('stdin', sa.Text(), nullable=False),
        sa.Column('expected', sa.Text(), nullable=False),
        sa.Column('is_sample', sa.Integer(), server_default='0'),
    )
    op.create_index(op.f('ix_test_cases_id'), 'test_cases', ['id'], unique=False)
    op.create_index(op.f('ix_test_cases_problem_id'), 'test_cases', ['problem_id'], unique=False)

    # ── submissions ────────────────────────────────────────────────────
    op.create_table(
        'submissions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('problem_id', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(20), nullable=False),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('verdict', sa.String(30), nullable=True),
        sa.Column('runtime_ms', sa.Float(), nullable=True),
        sa.Column('memory_kb', sa.Integer(), nullable=True),
        sa.Column('error_output', sa.Text(), nullable=True),
        sa.Column('ai_review', sa.Text(), nullable=True),
        sa.Column('is_sample_only', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('judged_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_submissions_id'), 'submissions', ['id'], unique=False)
    op.create_index(op.f('ix_submissions_user_id'), 'submissions', ['user_id'], unique=False)
    op.create_index(op.f('ix_submissions_problem_id'), 'submissions', ['problem_id'], unique=False)

    # ── contests ───────────────────────────────────────────────────────
    op.create_table(
        'contests',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('invite_code', sa.String(20), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_public', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(op.f('ix_contests_id'), 'contests', ['id'], unique=False)
    op.create_unique_constraint('uq_contests_invite_code', 'contests', ['invite_code'])

    # ── contest_problems ───────────────────────────────────────────────
    op.create_table(
        'contest_problems',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('contest_id', sa.Integer(), nullable=False),
        sa.Column('problem_id', sa.Integer(), nullable=False),
        sa.Column('points', sa.Integer(), server_default='100'),
    )
    op.create_index(op.f('ix_contest_problems_contest_id'), 'contest_problems', ['contest_id'], unique=False)

    # ── contest_participants ───────────────────────────────────────────
    op.create_table(
        'contest_participants',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('contest_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(op.f('ix_contest_participants_contest_id'), 'contest_participants', ['contest_id'], unique=False)
    op.create_index(op.f('ix_contest_participants_user_id'), 'contest_participants', ['user_id'], unique=False)


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('contest_participants')
    op.drop_table('contest_problems')
    op.drop_table('contests')
    op.drop_table('submissions')
    op.drop_table('test_cases')
    op.drop_table('problems')
    op.drop_table('users')
