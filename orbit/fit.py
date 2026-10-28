"""Does a Hugging Face model fit on a host's GPU?

V0.1 reads the parameter count and quantization from the model name, which is
how GGUF files on Hugging Face are commonly named (e.g. "Qwen2.5-7B-Instruct-Q4_K_M").
When the name does not say, the answer is "unknown", never a guess.
"""
import re
from dataclasses import dataclass

# Bytes per parameter by quantization. Q4 ~ 0.56, Q5 ~ 0.69, Q6 ~ 0.82, Q8 ~ 1.06, F16 = 2.
BYTES_PER_PARAM = {
    "Q2": 0.35, "Q3": 0.45, "Q4": 0.56, "Q5": 0.69, "Q6": 0.82, "Q8": 1.06,
    "F16": 2.0, "FP16": 2.0, "BF16": 2.0, "F32": 4.0,
}
OVERHEAD = 1.2  # room for the context window and runtime


@dataclass
class Fit:
    verdict: str          # fits | tight | too_big | unknown
    params_b: float | None
    quant: str | None
    needs_gb: float | None
    reason: str


def parse(model: str) -> tuple[float | None, str | None]:
    tail = model.split("/")[-1]
    m = re.search(r"(\d+(?:\.\d+)?)\s*[bB](?![a-zA-Z])", tail)
    params = float(m.group(1)) if m else None
    q = re.search(r"(?i)\b(Q[2-8]|F16|FP16|BF16|F32)", tail)
    quant = q.group(1).upper() if q else None
    return params, quant


def check(model: str, vram_gb: float) -> Fit:
    params, quant = parse(model)
    if params is None:
        return Fit("unknown", None, quant, None, "the model name does not say how many parameters it has")
    bpp = BYTES_PER_PARAM.get(quant or "", None)
    if bpp is None:
        return Fit("unknown", params, quant, None, "the model name does not say its quantization")
    needs = round(params * bpp * OVERHEAD, 1)
    if needs <= vram_gb * 0.9:
        return Fit("fits", params, quant, needs, f"needs about {needs} GB, host has {vram_gb} GB")
    if needs <= vram_gb:
        return Fit("tight", params, quant, needs, f"needs about {needs} GB, host has {vram_gb} GB, little room for context")
    return Fit("too_big", params, quant, needs, f"needs about {needs} GB, host has only {vram_gb} GB")
