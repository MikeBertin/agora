"""Concrete negotiation domains and preference profiles.

Job Offer: a candidate (A) and an employer (B) negotiate a contract over five
issues. Preferences are largely opposed on money/holiday/location but only
partially opposed on Role (the employer prefers a cost-effective Mid hire, not
the cheapest Junior), which is what creates win-win trades and a non-trivial
Pareto frontier.
"""
from __future__ import annotations

from .domain import Domain, UtilitySpace

JOB_OFFER = Domain("Job Offer", [
    ("Salary",   ["50k", "55k", "60k", "65k", "70k"]),
    ("Holiday",  ["20 days", "25 days", "30 days", "35 days"]),
    ("Role",     ["Junior", "Mid", "Senior", "Lead"]),
    ("Location", ["Office", "Hybrid", "Remote", "Flexible"]),
    ("Start",    ["Immediate", "1 month", "3 months"]),
])

# Candidate: wants money, holiday, seniority, remote, and time before starting.
CANDIDATE = UtilitySpace(
    JOB_OFFER,
    weights={"Salary": 0.35, "Holiday": 0.20, "Role": 0.20,
             "Location": 0.15, "Start": 0.10},
    evals={
        "Salary":   {"50k": 0.0, "55k": 0.25, "60k": 0.5, "65k": 0.75, "70k": 1.0},
        "Holiday":  {"20 days": 0.0, "25 days": 0.33, "30 days": 0.66, "35 days": 1.0},
        "Role":     {"Junior": 0.0, "Mid": 0.33, "Senior": 0.66, "Lead": 1.0},
        "Location": {"Office": 0.0, "Hybrid": 0.5, "Remote": 1.0, "Flexible": 0.8},
        "Start":    {"Immediate": 0.0, "1 month": 0.5, "3 months": 1.0},
    },
    reservation=0.3,
)

# Employer: wants to control cost, keep people in/near the office, start soon,
# and (single-peaked) hire at Mid level rather than the cheapest or priciest.
EMPLOYER = UtilitySpace(
    JOB_OFFER,
    weights={"Salary": 0.30, "Holiday": 0.15, "Role": 0.15,
             "Location": 0.25, "Start": 0.15},
    evals={
        "Salary":   {"50k": 1.0, "55k": 0.75, "60k": 0.5, "65k": 0.25, "70k": 0.0},
        "Holiday":  {"20 days": 1.0, "25 days": 0.66, "30 days": 0.33, "35 days": 0.0},
        "Role":     {"Junior": 0.4, "Mid": 1.0, "Senior": 0.6, "Lead": 0.3},
        "Location": {"Office": 1.0, "Hybrid": 0.7, "Remote": 0.2, "Flexible": 0.5},
        "Start":    {"Immediate": 1.0, "1 month": 0.5, "3 months": 0.0},
    },
    reservation=0.3,
)

PROFILES = {"job-offer": (JOB_OFFER, CANDIDATE, EMPLOYER)}
