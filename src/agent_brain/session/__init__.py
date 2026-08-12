"""Host-agnostic session start/end adapters (Codex / Claude / Cursor friendly)."""

from agent_brain.session.end import session_end
from agent_brain.session.start import session_start

__all__ = ["session_start", "session_end"]
