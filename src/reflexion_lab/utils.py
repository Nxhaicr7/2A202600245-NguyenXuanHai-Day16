from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Iterable
from .schemas import QAExample, RunRecord

def normalize_answer(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text

def load_dataset(path: str | Path) -> list[QAExample]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    examples = []
    for item in raw:
        if "qid" in item:
            examples.append(QAExample.model_validate(item))
        else:
            context_chunks = [{"title": title, "text": "".join(sentences)} for title, sentences in item.get("context", [])]
            examples.append(QAExample(
                qid=item.get("_id", "unknown"),
                difficulty=item.get("level", "medium"),
                question=item.get("question", ""),
                gold_answer=item.get("answer", ""),
                context=context_chunks
            ))
    return examples

def save_jsonl(path: str | Path, records: Iterable[RunRecord]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(record.model_dump_json() + "\n")
