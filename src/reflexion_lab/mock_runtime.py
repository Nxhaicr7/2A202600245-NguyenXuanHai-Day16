import time
import requests
import json
from .schemas import QAExample, JudgeResult, ReflectionEntry
from .prompts import ACTOR_SYSTEM, EVALUATOR_SYSTEM, REFLECTOR_SYSTEM

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"

def call_ollama(prompt: str, system: str, format_json: bool = False) -> tuple[str, int, float]:
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "temperature": 0.1
        }
    }
    if format_json:
        payload["format"] = "json"
        
    start_time = time.time()
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        latency = (time.time() - start_time) * 1000
        
        text = data.get("response", "").strip()
        tokens = data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
        return text, tokens, latency
    except Exception as e:
        latency = (time.time() - start_time) * 1000
        print(f"Ollama API error: {e}")
        return "{}" if format_json else "Error", 0, latency

def actor_answer(example: QAExample, attempt_id: int, agent_type: str, reflection_memory: list[ReflectionEntry]) -> tuple[str, int, float]:
    context_str = "\n".join([f"- {c.title}: {c.text}" for c in example.context])
    
    prompt = f"Question: {example.question}\nContext:\n{context_str}\n"
    
    if agent_type == "reflexion" and reflection_memory:
        reflections_str = "\n".join([f"Attempt {r.attempt_id} failed. Critique: {r.critique}. Strategy: {r.strategy}" for r in reflection_memory])
        prompt += f"\nPrevious failed attempts and strategies:\n{reflections_str}\n"
        prompt += "\nPlease use the strategy above to provide a better answer."
        
    response, tokens, latency = call_ollama(prompt, ACTOR_SYSTEM, format_json=False)
    return response, tokens, latency

def evaluator(example: QAExample, answer: str) -> tuple[JudgeResult, int, float]:
    prompt = f"Question: {example.question}\nReference Answer: {example.gold_answer}\nActor Answer: {answer}"
    
    response, tokens, latency = call_ollama(prompt, EVALUATOR_SYSTEM, format_json=True)
    try:
        data = json.loads(response)
        score = int(data.get("score", 0))
        reason = str(data.get("reason", "No reason provided"))
        return JudgeResult(
            score=score,
            reason=reason,
            is_passed=(score == 1),
            flaws=[] if score == 1 else [reason],
            suggestions="N/A"
        ), tokens, latency
    except Exception as e:
        return JudgeResult(
            score=0,
            reason=f"Failed to parse JSON: {e}. Raw response: {response}",
            is_passed=False,
            flaws=[],
            suggestions=""
        ), tokens, latency

def reflector(example: QAExample, attempt_id: int, judge: JudgeResult) -> tuple[ReflectionEntry, int, float]:
    prompt = f"Question: {example.question}\nFailed due to: {judge.reason}\nProvide a short diagnosis and strategy."
    response, tokens, latency = call_ollama(prompt, REFLECTOR_SYSTEM, format_json=False)
    
    diagnosis = "Unknown diagnosis"
    strategy = "Read context carefully"
    
    for line in response.split('\n'):
        if line.lower().startswith('diagnosis:'):
            diagnosis = line.split(':', 1)[1].strip()
        elif line.lower().startswith('strategy:'):
            strategy = line.split(':', 1)[1].strip()
            
    if diagnosis == "Unknown diagnosis" and "Strategy:" not in response:
        diagnosis = response
    
    entry = ReflectionEntry(
        attempt_id=attempt_id,
        lesson=diagnosis,
        strategy=strategy,
        critique=judge.reason,
        improvement_plan=strategy
    )
    return entry, tokens, latency

def determine_failure_mode(judge_reason: str, reflection_memory: list[ReflectionEntry]) -> str:
    r = judge_reason.lower()
    if len(reflection_memory) >= 2:
        return "looping"
    if "drift" in r or "wrong entity" in r or "second paragraph" in r:
        return "entity_drift"
    if "incomplete" in r or "hop" in r or "partial" in r:
        return "incomplete_multi_hop"
    if "hallucinat" in r or "overfit" in r:
        return "reflection_overfit"
    return "wrong_final_answer"
