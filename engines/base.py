from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from time import perf_counter


@dataclass
class OCRResult:
    engine: str
    lines: list[str] = field(default_factory=list)
    full_text: str = ""
    confidence: float = 0.0
    elapsed_ms: int = 0
    error: str = ""

    def to_dict(self) -> dict:
        return self.__dict__


class OCREngine(ABC):
    name: str = "base"

    @abstractmethod
    def _run(self, image_paths: list[str]) -> tuple[list[str], float]:
        """Return (lines, mean_confidence 0-1)."""
        ...

    def extract(self, image_paths: list[str]) -> OCRResult:
        t0 = perf_counter()
        try:
            lines, conf = self._run(image_paths)
            return OCRResult(
                engine=self.name,
                lines=lines,
                full_text="\n".join(lines),
                confidence=round(conf, 3),
                elapsed_ms=int((perf_counter() - t0) * 1000),
            )
        except Exception as e:
            return OCRResult(
                engine=self.name,
                elapsed_ms=int((perf_counter() - t0) * 1000),
                error=str(e),
            )
