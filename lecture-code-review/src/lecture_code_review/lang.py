from __future__ import annotations


_EXT_BY_LANG = {
    "C": "c",
    "C++": "cpp",
    "Java": "java",
    "Python3": "py",
    "Python2": "py",
    "Go": "go",
    "Rust": "rs",
    "JavaScript": "js",
    "Kotlin": "kt",
    "C#": "cs",
}


def ext_for(language: str | None) -> str:
    if not language:
        return "txt"
    return _EXT_BY_LANG.get(language, "txt")


# Mirrors Backend/submission/models.py:13 JudgeStatus (do not import from backend).
RESULT_LABELS = {
    -2: "CE",       # COMPILE_ERROR
    -1: "WA",       # WRONG_ANSWER
    0: "AC",        # ACCEPTED
    1: "TLE",       # CPU_TIME_LIMIT_EXCEEDED
    2: "RTLE",      # REAL_TIME_LIMIT_EXCEEDED
    3: "MLE",       # MEMORY_LIMIT_EXCEEDED
    4: "RE",        # RUNTIME_ERROR
    5: "SE",        # SYSTEM_ERROR
    6: "PENDING",
    7: "JUDGING",
    8: "PA",        # PARTIALLY_ACCEPTED
}

PENDING_RESULTS = {6, 7}


def result_label(code: int | None) -> str:
    if code is None:
        return "UNKNOWN"
    return RESULT_LABELS.get(code, f"R{code}")
