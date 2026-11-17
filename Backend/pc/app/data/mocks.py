"""mock 数据装配：内容全部来自 data/mock/*.json，按学号确定性抽取。"""

from __future__ import annotations

import random

from ..models import Bullet, Course, Experience, StudentProfile
from .mock_store import load


def _experience(item, with_period: bool) -> Experience:
    return Experience(
        title=item.title,
        org=item.org,
        start=item.start if with_period else "",
        end=item.end if with_period else "",
        bullets=[Bullet(text=b, source="mock") for b in item.bullets],
    )


def _pick(rng: random.Random, items: list, k: int) -> list:
    if not items:
        return []
    return rng.sample(items, min(k, len(items)))


def build_mock(student: StudentProfile) -> dict:
    bundle = load()
    rng = random.Random(student.id)
    entry = bundle.academic.get(student.id)

    if entry is not None:
        gpa = entry.gpa
        rank = entry.rank
        cet4 = entry.cet4
        cet6 = entry.cet6
        courses = [
            Course(name=c.name, score=c.score, credit=c.credit) for c in entry.courses
        ]
    else:
        gpa = round(rng.uniform(3.1, 3.9), 2)
        rank = f"{rng.randint(3, 28)}/96"
        cet4 = rng.choice([0, 528, 551, 496, 487])
        cet6 = rng.choice([0, 0, 476, 452, 503])
        names = _pick(rng, bundle.pools.courses, 8)
        courses = [
            Course(name=n, score=round(rng.uniform(78, 98), 1), credit=rng.choice([2, 3, 4]))
            for n in names
        ]

    projects = [_experience(p, with_period=False) for p in _pick(rng, bundle.experiences.projects, 2)]
    internships = [
        _experience(i, with_period=True) for i in _pick(rng, bundle.experiences.internships, 1)
    ]

    return {
        "gpa": gpa,
        "rank": rank,
        "cet4": cet4,
        "cet6": cet6,
        "courses": courses,
        "skills": list(bundle.pools.skills),
        "projects": projects,
        "internships": internships,
        "certificates": _pick(rng, bundle.pools.certificates, 3),
        "awards": _pick(rng, bundle.pools.awards, 2),
    }
