"""Pictures in place of sentences.

An author turns a scene into words. These functions do the reverse: each sentence the site
would otherwise say is drawn as a shape, so a person reads the idea at a glance.

    "The model runs on your machine."        a comet in orbit around a glowing core
    "Any open model."                        several comets, each on its own lane
    "You reach it from any browser."         a phone outside the orbits, joined to the core
    "Your words travel sealed."              a closed capsule moves along that line
    "The relay cannot open them."            the capsule passes a hollow gate and stays closed
    "Only your machine reads them."          the core pulses when the capsule arrives
    "This model fits that machine."          a disc inside a ring; too big, and it spills over

Everything is plain SVG with classes. No inline style and no script, so the content security
policy holds, and style.css stops all motion for people who ask for less of it.
"""
import math
import random

from markupsafe import Markup

TAU = math.tau


def _pt(r: float, deg: float) -> tuple[float, float]:
    a = math.radians(deg)
    return round(r * math.cos(a), 2), round(r * math.sin(a), 2)


def _arc(r: float, a0: float, a1: float) -> str:
    """Path for an arc of radius r around 0,0 from angle a0 to a1 (degrees, clockwise on screen)."""
    (x0, y0), (x1, y1) = _pt(r, a0), _pt(r, a1)
    large = 1 if abs(a1 - a0) > 180 else 0
    sweep = 1 if a1 > a0 else 0
    return f"M{x0} {y0}A{r} {r} 0 {large} {sweep} {x1} {y1}"


def _comet(r: float, tone: str, size: float = 1.0) -> str:
    """A comet with its head at angle 0: a thin faint tail behind, a bright head with a halo."""
    tail = "".join(
        f'<path class="tail" d="{_arc(r, -length, 0)}" stroke-width="{round(width * size, 2)}" opacity="{alpha}"/>'
        for length, width, alpha in ((110, 1.0, 0.14), (74, 1.6, 0.26), (42, 2.4, 0.5), (16, 3.2, 0.9)))
    return (f'<g class="comet {tone}">{tail}'
            f'<circle class="halo" cx="{r}" cy="0" r="{round(11 * size, 1)}"/>'
            f'<circle class="head" cx="{r}" cy="0" r="{round(5 * size, 1)}"/>'
            f'<circle class="eye" cx="{r}" cy="0" r="{round(1.8 * size, 1)}"/></g>')


def _stars(n: int, x0: int, y0: int, w: int, h: int, seed: int = 7) -> str:
    rng = random.Random(seed)  # the same sky on every page load
    return "".join(
        f'<circle class="star t{rng.randint(1, 3)}" cx="{rng.randint(x0, x0 + w)}" cy="{rng.randint(y0, y0 + h)}" r="{rng.choice((0.6, 0.8, 1.1))}"/>'
        for _ in range(n))


def _core(r: float = 24) -> str:
    """Your machine: a small sun. Layers of glow, and rays that turn slowly."""
    rays = "".join(
        '<line x1="{}" y1="{}" x2="{}" y2="{}"/>'.format(*_pt(r + 9, d), *_pt(r + (19 if i % 2 else 14), d))
        for i, d in enumerate(range(0, 360, 30)))
    return (f'<g class="core"><circle class="glow g3" r="{r * 2.9}"/><circle class="glow g2" r="{r * 2.0}"/>'
            f'<circle class="glow g1" r="{r * 1.4}"/><g class="rays">{rays}</g>'
            f'<circle class="sun" r="{r}"/><circle class="pulse" r="{r}"/></g>')


def _phone(x: float, y: float) -> str:
    return (f'<g class="phone" transform="translate({x} {y})"><rect x="-13" y="-22" width="26" height="44" rx="6"/>'
            '<rect class="screen" x="-9" y="-16" width="18" height="29" rx="2.5"/><circle class="ping" r="20"/></g>')


def _capsule(cls: str, tilt: float) -> str:
    """A sealed envelope on its way: a closed pill with a small lock."""
    return (f'<g class="capsule {cls}"><g transform="rotate({tilt})"><rect x="-10" y="-6.5" width="20" height="13" rx="6.5"/>'
            '<path class="lock" d="M-2.6 -0.5v-1.6a2.6 2.6 0 0 1 5.2 0v1.6"/><rect class="lock-body" x="-3.6" y="-0.8" width="7.2" height="5" rx="1.2"/></g></g>')


def hero() -> Markup:
    """The whole idea in one picture."""
    px, py = -244, 126                 # the phone
    gx, gy = -153, 79                  # the relay's gate, on the line from the phone to the core
    tilt = round(math.degrees(math.atan2(-py, -px)), 1)
    lanes = "".join(f'<circle class="lane" r="{r}"/>' for r in (84, 116, 148))
    comets = (f'<g class="orbit o1">{_comet(84, "blue", 0.9)}</g><g class="orbit o2">{_comet(116, "violet", 1.1)}</g>'
              f'<g class="orbit o3">{_comet(148, "mint", 0.8)}</g>')
    return Markup(
        '<svg class="scene hero-scene" viewBox="-284 -196 476 392" role="img" '
        'aria-label="Open models orbit your own machine. A sealed message travels from any browser, through a relay that cannot open it, to your machine.">'
        f'{_stars(46, -284, -196, 476, 392)}{lanes}'
        f'<line class="link" x1="{px + 15}" y1="{py - 8}" x2="0" y2="0"/>'
        f'{comets}{_core()}'
        f'<g class="gate" transform="translate({gx} {gy})"><circle class="gate-glow" r="17"/><circle class="gate-ring" r="10"/></g>'
        f'{_phone(px, py)}{_capsule("out", tilt)}{_capsule("back", tilt)}'
        '<text class="lbl strong" x="0" y="54">your machine</text>'
        '<text class="lbl" x="0" y="-164">any open model</text>'
        f'<text class="lbl" x="{px}" y="{py - 34}">any browser</text>'
        f'<text class="lbl strong" x="{gx + 6}" y="{gy + 32}">relay</text>'
        f'<text class="lbl dim" x="{gx + 6}" y="{gy + 47}">cannot open it</text>'
        '</svg>')


def fit(needs_gb: float | None, has_gb: float, verdict: str, size: int = 56) -> Markup:
    """Does it fit? The ring is the machine's memory. The disc is the model. Areas are to scale."""
    ring = 21.0
    if needs_gb is None or has_gb <= 0:
        inner = f'<circle class="fit-disc" r="{ring * 0.55}"/><text class="fit-q" y="5">?</text>'
    else:
        r = min(ring * math.sqrt(needs_gb / has_gb), ring * 1.32)   # area is to scale, until it would leave the picture
        inner = f'<circle class="fit-disc" r="{round(max(r, 2.5), 1)}"/>'
    words = {"fits": "fits", "tight": "a tight fit", "too_big": "too big", "unknown": "unknown"}[verdict]
    return Markup(f'<svg class="fit {verdict}" width="{size}" height="{size}" viewBox="-30 -30 60 60" role="img" aria-label="{words}">'
                  f'{inner}<circle class="fit-ring" r="{ring}"/></svg>')


def glyph(phase: str) -> Markup:
    """The session at a glance: loading, in orbit, or at rest."""
    comet = _comet(17, "blue", 0.55)
    return Markup(f'<svg class="glyph {phase}" width="52" height="52" viewBox="-26 -26 52 52" aria-hidden="true">'
                  f'<circle class="lane" r="17"/><g class="orbit o0">{comet}</g>'
                  '<circle class="glow g1" r="9"/><circle class="sun" r="5.5"/></svg>')


def step(n: int) -> Markup:
    """Three small pictures for the three things a person does."""
    if n == 1:      # add your machine: a core lights up
        body = f'<circle class="lane" r="30"/>{_core(11)}'
    elif n == 2:    # pick a model: a comet joins the orbit
        body = f'<circle class="lane" r="30"/><g class="orbit o0">{_comet(30, "violet", 0.8)}</g><circle class="glow g1" r="15"/><circle class="sun" r="9"/>'
    else:           # talk from anywhere: a sealed capsule between a phone and the core
        body = ('<line class="link" x1="-30" y1="14" x2="22" y2="-10"/><circle class="glow g1" cx="24" cy="-11" r="15"/>'
                '<circle class="sun" cx="24" cy="-11" r="9"/>'
                '<g class="phone small" transform="translate(-34 16) scale(.62)"><rect x="-13" y="-22" width="26" height="44" rx="6"/>'
                '<rect class="screen" x="-9" y="-16" width="18" height="29" rx="2.5"/></g>'
                '<g class="capsule still" transform="translate(-5 2) rotate(-25) scale(.8)"><rect x="-10" y="-6.5" width="20" height="13" rx="6.5"/>'
                '<path class="lock" d="M-2.6 -0.5v-1.6a2.6 2.6 0 0 1 5.2 0v1.6"/><rect class="lock-body" x="-3.6" y="-0.8" width="7.2" height="5" rx="1.2"/></g>')
    return Markup(f'<svg class="scene mini" viewBox="-48 -40 96 80" aria-hidden="true">{body}</svg>')


def path() -> Markup:
    """Who reads the words: the browser and the machine do. The relay between them does not."""
    def letter(x: int, is_open: bool) -> str:
        if is_open:   # an open page: lines of text
            lines = "".join(f'<line class="ink" x1="{x - 13}" y1="{y}" x2="{x + (13 if i != 2 else 3)}" y2="{y}"/>' for i, y in enumerate((-7, 0, 7)))
            return f'<rect class="page" x="{x - 21}" y="-17" width="42" height="34" rx="6"/>{lines}'
        return (f'<rect class="sealed" x="{x - 21}" y="-15" width="42" height="30" rx="6"/>'
                f'<path class="flap" d="M{x - 21} -11l21 15l21 -15"/>')
    return Markup(
        '<svg class="scene path" viewBox="-200 -62 400 124" role="img" '
        'aria-label="Your browser and your machine read the words. The relay between them sees only a sealed envelope.">'
        '<line class="link" x1="-118" y1="0" x2="-34" y2="0"/><line class="link" x1="34" y1="0" x2="118" y2="0"/>'
        f'{letter(-150, True)}{letter(0, False)}{letter(150, True)}'
        '<text class="lbl strong" x="-150" y="-32">your browser</text><text class="lbl strong" x="0" y="-32">relay</text>'
        '<text class="lbl strong" x="150" y="-32">your machine</text>'
        '<text class="lbl ok" x="-150" y="42">reads it</text><text class="lbl no" x="0" y="42">cannot read it</text>'
        '<text class="lbl ok" x="150" y="42">reads it</text></svg>')
