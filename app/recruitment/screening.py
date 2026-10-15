"""Recruitment screening use case: end-to-end resume triage.

Flow: free-text job description and resume -> LLM structured extraction ->
deterministic rubric scoring -> a screening report with evidence.

The LLM is used only to parse unstructured text into a schema. The hiring
decision itself is deterministic and auditable, so the same inputs always
produce the same score and the reasoning can be shown to a reviewer.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from app.llm.client import complete_json

_NON_WORD = re.compile(r"[^a-z0-9+#. ]")

ADVANCE_THRESHOLD = 75
HOLD_THRESHOLD = 50


class ScreenRequest(BaseModel):
    """A job description and a candidate resume, both free text."""

    job_description: str = Field(min_length=10)
    resume: str = Field(min_length=10)


class JobRequirements(BaseModel):
    role: str
    required_skills: list[str]
    min_years: float
    nice_to_have: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)


class CandidateProfile(BaseModel):
    name: str
    years_experience: float
    skills: list[str]
    education: str = ""
    highlights: list[str] = Field(default_factory=list)


class CriterionEvidence(BaseModel):
    criterion: str
    matched: bool
    detail: str


class ScreeningReport(BaseModel):
    """The end-to-end screening result shown to a recruiter."""

    candidate: CandidateProfile
    requirements: JobRequirements
    match_score: float
    recommendation: str  # advance | hold | reject
    matched_skills: list[str]
    missing_skills: list[str]
    evidence: list[CriterionEvidence]
    model: str
    route: str
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float
    latency_ms: float


def _normalize(value: str) -> str:
    return _NON_WORD.sub(" ", value.lower()).strip()


def _skill_matches(skill: str, candidate_skills: list[str]) -> bool:
    """True when a required skill is present in the candidate's skill list.

    Matches on normalized substring in either direction so "python" matches
    "python 3" and "ci/cd" matches "ci cd pipelines".
    """
    target = _normalize(skill)
    if not target:
        return False
    for candidate in candidate_skills:
        normalized = _normalize(candidate)
        if target in normalized or normalized in target:
            return True
    return False


def score_candidate(
    profile: CandidateProfile, requirements: JobRequirements
) -> tuple[float, list[str], list[str], list[CriterionEvidence]]:
    """Score a profile against requirements. Deterministic and explainable.

    Weighting: 75% required-skill coverage, 25% experience vs. the stated
    minimum. Nice-to-have skills add up to a 5-point bonus. The result is
    capped at 100.
    """
    required = requirements.required_skills or []
    matched = [s for s in required if _skill_matches(s, profile.skills)]
    missing = [s for s in required if not _skill_matches(s, profile.skills)]
    coverage = len(matched) / len(required) if required else 1.0

    if requirements.min_years > 0:
        experience_factor = min(1.0, profile.years_experience / requirements.min_years)
    else:
        experience_factor = 1.0

    nice = requirements.nice_to_have or []
    nice_matched = [s for s in nice if _skill_matches(s, profile.skills)]
    nice_ratio = len(nice_matched) / len(nice) if nice else 0.0

    raw = 100 * (0.75 * coverage + 0.25 * experience_factor) + 5 * nice_ratio
    score = round(min(100.0, raw), 1)

    evidence = [
        CriterionEvidence(
            criterion=f"Required skill: {skill}",
            matched=_skill_matches(skill, profile.skills),
            detail=(
                "found in resume"
                if _skill_matches(skill, profile.skills)
                else "not found"
            ),
        )
        for skill in required
    ]
    evidence.append(
        CriterionEvidence(
            criterion=f"Minimum experience: {requirements.min_years} years",
            matched=profile.years_experience >= requirements.min_years,
            detail=f"candidate has {profile.years_experience} years",
        )
    )
    for skill in nice:
        evidence.append(
            CriterionEvidence(
                criterion=f"Nice to have: {skill}",
                matched=_skill_matches(skill, profile.skills),
                detail=(
                    "found in resume"
                    if _skill_matches(skill, profile.skills)
                    else "not found"
                ),
            )
        )
    return score, matched, missing, evidence


def _recommendation(score: float) -> str:
    if score >= ADVANCE_THRESHOLD:
        return "advance"
    if score >= HOLD_THRESHOLD:
        return "hold"
    return "reject"


_JD_PROMPT = """You are a technical recruiter. Extract the requirements from this job description.

Respond with ONLY valid JSON matching this structure:
{{
  "role": "job title",
  "required_skills": ["skill", "..."],
  "min_years": 0,
  "nice_to_have": ["skill", "..."],
  "responsibilities": ["...", "..."]
}}

Job description:
{text}"""

_RESUME_PROMPT = """You are a resume parser. Extract a structured candidate profile.

Respond with ONLY valid JSON matching this structure:
{{
  "name": "candidate name or 'Unknown'",
  "years_experience": 0,
  "skills": ["skill", "..."],
  "education": "highest qualification",
  "highlights": ["notable achievement", "..."]
}}

Resume:
{text}"""


async def screen(request: ScreenRequest) -> ScreeningReport:
    """Run the full screening pipeline and return an auditable report."""
    requirements_data, jd_meta = await complete_json(
        _JD_PROMPT.format(text=request.job_description)
    )
    profile_data, resume_meta = await complete_json(
        _RESUME_PROMPT.format(text=request.resume)
    )

    requirements = JobRequirements(**requirements_data)
    profile = CandidateProfile(**profile_data)
    score, matched, missing, evidence = score_candidate(profile, requirements)

    return ScreeningReport(
        candidate=profile,
        requirements=requirements,
        match_score=score,
        recommendation=_recommendation(score),
        matched_skills=matched,
        missing_skills=missing,
        evidence=evidence,
        model=resume_meta["model"],
        route=resume_meta["route"],
        prompt_tokens=jd_meta["prompt_tokens"] + resume_meta["prompt_tokens"],
        completion_tokens=jd_meta["completion_tokens"]
        + resume_meta["completion_tokens"],
        estimated_cost_usd=round(
            jd_meta["estimated_cost_usd"] + resume_meta["estimated_cost_usd"], 6
        ),
        latency_ms=round(jd_meta["latency_ms"] + resume_meta["latency_ms"], 2),
    )
