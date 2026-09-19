from dataclasses import dataclass, field


@dataclass
class TranscriptSegment:
    id: str
    text: str
    speaker_id: str | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None


@dataclass
class DocumentJob:
    id: str
    document_id: str
    state: str = "queued"
    progress: int = 0
    transcript: str = ""
    segments: list[TranscriptSegment] = field(default_factory=list)
