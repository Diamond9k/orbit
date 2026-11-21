"""The pictures: each one must say its sentence, and none may carry script or inline style."""
import os
import re

import pytest
from fastapi.testclient import TestClient

from orbit import db, scene
from orbit.app import app, short_model


def _radius(svg):
    svg = str(svg)
    return float(re.search(r'class="fit-disc" r="([\d.]+)"', svg).group(1))


def test_no_picture_has_script_or_inline_style():
    for svg in (scene.hero(), scene.path(), scene.glyph("running"), scene.step(1), scene.step(2), scene.step(3),
                scene.fit(4.7, 8, "fits"), scene.fit(None, 8, "unknown")):
        svg = str(svg)
        assert "<script" not in svg and " style=" not in svg and not re.search(r"\son\w+=", svg)


def test_the_hero_shows_every_part_of_the_idea():
    svg = str(scene.hero())
    for part in ("your machine", "any open model", "any browser", "relay", "cannot open it"):
        assert part in svg
    assert svg.count('class="comet') == 3 and 'class="capsule out"' in svg and 'class="capsule back"' in svg
    assert "aria-label=" in svg       # a person who cannot see it is told the same thing in words


def test_the_fit_disc_is_to_scale():
    half, full, over = _radius(scene.fit(12, 24, "fits")), _radius(scene.fit(24, 24, "tight")), _radius(scene.fit(47, 24, "too_big"))
    assert half < full < over
    assert round((half / full) ** 2, 2) == 0.5      # half the memory is half the area
    assert full == 21.0 and over > 21.0             # full memory fills the ring; too big spills past it
    assert 'class="fit-q"' in str(scene.fit(None, 24, "unknown"))   # unknown is drawn as unknown, never as a guess


def test_the_path_says_who_reads_the_words():
    svg = str(scene.path())
    assert svg.count(">reads it<") == 2 and svg.count(">cannot read it<") == 1


def test_a_model_has_a_short_name():
    assert short_model("bartowski/Qwen2.5-7B-Instruct-GGUF Q4_K_M") == "Qwen2.5-7B-Instruct"
    assert short_model("x/Model-7B-Q4_K_M") == "Model-7B-Q4_K_M"


@pytest.fixture
def client():
    db.init(os.environ["ORBIT_DB"])
    with TestClient(app) as c:
        yield c


def test_the_start_page_is_a_picture_with_few_words(client):
    page = client.get("/").text
    assert 'class="scene hero-scene"' in page
    words = re.sub(r"<svg.*?</svg>|<script.*?</script>|<[^>]+>", " ", page, flags=re.S).split()
    assert len(words) < 130, len(words)             # it was about 330 before the pictures took over
    assert "fit-strip" in client.get("/?model=x/Model-7B-Q4_K_M").text
