from orbit import fit


def test_parses_params_and_quant():
    assert fit.parse("bartowski/Qwen2.5-7B-Instruct-GGUF Q4_K_M") == (7.0, "Q4")
    assert fit.parse("Meta-Llama-3.1-8B-Instruct-Q8_0.gguf") == (8.0, "Q8")
    assert fit.parse("some-model") == (None, None)


def test_verdicts():
    assert fit.check("x/Model-7B-Q4_K_M", 12).verdict == "fits"
    assert fit.check("x/Model-70B-Q4_K_M", 24).verdict == "too_big"
    assert fit.check("x/Model-7B", 24).verdict == "unknown"
    assert fit.check("x/Mystery", 24).verdict == "unknown"


def test_tight_band():
    # 13B at Q4: 13 * 0.56 * 1.2 = 8.7 GB. On 9 GB that is between 90% and 100%.
    assert fit.check("x/Model-13B-Q4_K_M", 9).verdict == "tight"
