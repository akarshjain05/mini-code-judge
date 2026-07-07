"""
AI Code Review endpoint using Google Gemini (free tier).
POST /submissions/{id}/ai-review
"""
import os
import json
import asyncio
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.submission import Submission
from app.models.problem import Problem

router = APIRouter(tags=["ai-review"])

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
# gemini-2.0-flash was deprecated Feb 2026 and fully retired June 1 2026.
# gemini-2.5-flash-lite is Google's recommended free-tier migration target —
# same pricing tier as 2.0-flash but with a higher daily/per-minute quota,
# which gives more headroom against repeated testing.
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"


def _build_prompt(submission: Submission, problem: Problem) -> str:
    verdict = submission.verdict or submission.status
    lang_name = {"cpp": "C++", "c": "C", "java": "Java", "python": "Python"}.get(submission.language, submission.language)

    prompt = f"""You are an expert competitive programming coach reviewing a student's code submission.

Problem: {problem.title}
Description: {problem.description}

Student's {lang_name} Code:
```{submission.language}
{submission.code}
```

Verdict: {verdict.upper().replace('_', ' ')}"""

    if submission.runtime_ms:
        prompt += f"\nRuntime: {submission.runtime_ms:.1f}ms"
    if submission.error_output and submission.error_output not in ('SAMPLE_ONLY',):
        prompt += f"\nError Output:\n{submission.error_output[:500]}"

    prompt += """

Please provide a structured review with EXACTLY these section headers:

## Complexity
Time and space complexity of their solution with brief explanation.

## What Went Wrong
"""
    if verdict == "accepted":
        prompt += "Their solution is correct! Mention what they did well."
    elif verdict == "wrong_answer":
        prompt += "Explain exactly why the output is wrong. Give a specific counter-example if possible."
    elif verdict == "time_limit_exceeded":
        prompt += "Explain why this solution is too slow and what the bottleneck is."
    elif verdict == "compile_error":
        prompt += "Explain the compilation error in simple terms a student can understand."
    elif verdict == "runtime_error":
        prompt += "Explain what causes this runtime error (segfault, index out of bounds, etc)."
    else:
        prompt += "Analyze what caused this verdict."

    prompt += """

## Improvements
List 2-3 specific, actionable improvements to make their code better.

## Alternative Approach
Briefly describe a different algorithmic approach (2-3 sentences).

## Summary
One encouraging sentence summarizing the review.

Be concise, specific, and encouraging. Use backticks for code snippets."""

    return prompt


def _friendly_error(status_code: int, body_text: str) -> str:
    """Turn Gemini's raw JSON error body into a short, human-readable message."""
    try:
        body = json.loads(body_text)
        message = body.get("error", {}).get("message", "")
    except Exception:
        message = ""

    if status_code == 429:
        if "PerDay" in message or "daily" in message.lower():
            return "AI review has hit its daily limit. Please try again tomorrow."
        return "AI service is busy right now (rate limit). Please wait a minute and try again."
    if status_code == 503:
        return "AI service is temporarily overloaded. Please try again shortly."
    if status_code in (400, 401, 403):
        return "AI review is misconfigured (invalid or unauthorized API key). Contact the admin."
    return f"AI review failed (error {status_code}). Please try again."


async def _call_gemini(client: httpx.AsyncClient, prompt: str):
    return await client.post(
        f"{GEMINI_URL}?key={GEMINI_API_KEY}",
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1024,
            }
        },
    )


@router.post("/submissions/{submission_id}/ai-review")
async def get_ai_review(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your submission")
    if submission.status in ("pending", "running"):
        raise HTTPException(status_code=400, detail="Wait for judging to complete first")

    # Return cached review
    if submission.ai_review:
        return {"review": submission.ai_review, "cached": True}

    problem = db.query(Problem).filter(Problem.id == submission.problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    if not GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="AI review not configured. Admin needs to set GEMINI_API_KEY.")

    prompt = _build_prompt(submission, problem)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await _call_gemini(client, prompt)

            # One short retry specifically for 429/503 — RPM limits are a
            # rolling window and often clear within a couple seconds, and
            # Gemini's free tier frequently returns a transient 503 "model
            # overloaded" that clears just as quickly on retry.
            if response.status_code in (429, 503):
                await asyncio.sleep(3)
                response = await _call_gemini(client, prompt)

            if response.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=_friendly_error(response.status_code, response.text),
                )

            data = response.json()
            review_text = data["candidates"][0]["content"]["parts"][0]["text"]

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI review timed out. Try again.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="AI review failed unexpectedly. Try again.")

    # Cache in DB
    try:
        submission.ai_review = review_text
        db.commit()
    except Exception:
        db.rollback()

    return {"review": review_text, "cached": False}
