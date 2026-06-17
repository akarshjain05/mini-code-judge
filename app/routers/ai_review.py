"""
AI Code Review endpoint.
POST /submissions/{id}/ai-review
  → Fetches the submission, calls Claude API, returns structured review.
  → Caches result in DB so repeated calls don't re-bill the API.
"""
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import Column, Text
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.submission import Submission
from app.models.problem import Problem

router = APIRouter(tags=["ai-review"])

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-6"


def _build_prompt(submission: Submission, problem: Problem) -> str:
    verdict = submission.verdict or submission.status
    lang_name = {
        "cpp": "C++", "c": "C", "java": "Java", "python": "Python"
    }.get(submission.language, submission.language)

    prompt = f"""You are an expert competitive programming coach reviewing a student's code submission.

Problem: {problem.title}
Description: {problem.description}

Student's {lang_name} Code:
```{submission.language}
{submission.code}
```

Verdict: {verdict.upper().replace('_', ' ')}
"""
    if submission.runtime_ms:
        prompt += f"Runtime: {submission.runtime_ms:.1f}ms\n"
    if submission.error_output and submission.error_output != 'SAMPLE_ONLY':
        prompt += f"Error Output:\n{submission.error_output[:500]}\n"

    prompt += """
Please provide a structured code review with these exact sections:

## Complexity
State the time complexity and space complexity of their solution (e.g. O(n log n) time, O(n) space). Explain why briefly.

## What Went Wrong
"""
    if verdict == "accepted":
        prompt += "Their solution is correct! Mention what they did well."
    elif verdict == "wrong_answer":
        prompt += "Explain exactly why the output is wrong. Give a specific example input that breaks it if possible."
    elif verdict == "time_limit_exceeded":
        prompt += "Explain why this solution is too slow and what the bottleneck is."
    elif verdict == "compile_error":
        prompt += "Explain the compilation error in simple terms."
    elif verdict == "runtime_error":
        prompt += "Explain what causes this runtime error (segfault, index out of bounds, etc.)."
    else:
        prompt += "Analyze the issue based on the verdict."

    prompt += """

## Improvements
List 2-3 specific, actionable improvements to make their code better (faster, cleaner, or more correct).

## Alternative Approach
Briefly describe a different algorithmic approach they could use. Keep it to 2-3 sentences.

## Summary
One encouraging sentence summarizing the review.

Keep each section concise and specific. Use backticks for code. Be encouraging but honest."""

    return prompt


@router.post("/submissions/{submission_id}/ai-review")
async def get_ai_review(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Fetch submission
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your submission")
    if submission.status in ("pending", "running"):
        raise HTTPException(status_code=400, detail="Wait for judging to complete first")

    # Return cached review if exists
    if hasattr(submission, 'ai_review') and submission.ai_review:
        return {"review": submission.ai_review, "cached": True}

    # Fetch problem
    problem = db.query(Problem).filter(Problem.id == submission.problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="AI review not configured. Admin needs to set ANTHROPIC_API_KEY.")

    # Call Claude API
    prompt = _build_prompt(submission, problem)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": CLAUDE_MODEL,
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            if response.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Claude API error: {response.text[:200]}")

            data = response.json()
            review_text = data["content"][0]["text"]

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI review timed out. Try again.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI review failed: {str(e)}")

    # Cache in DB if column exists
    try:
        submission.ai_review = review_text
        db.commit()
    except Exception:
        db.rollback()

    return {"review": review_text, "cached": False}
