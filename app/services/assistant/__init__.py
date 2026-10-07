"""Conversational assistant package (typed chat + optional voice).

Two AI systems stay separate by design:
- TIMETABLE AI: fitted local model -> candidate scores -> existing solver.
- ASSISTANT: typed/voice input -> rule-based intent -> strict tools below.

The assistant only calls these tools. It never runs SQL or Python, never
bypasses ConflictService, and never touches the timetable model directly.
"""
