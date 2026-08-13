"""
being-human -- the demo reel.

Render (1080x1080, for LinkedIn):
    manim -qh -r 1080,1080 demo/scene.py BeingHumanDemo

Every number on screen is measured, not invented. They come from the corpus in
this repo's README: 1,187 messages, 42,477 words, and the before/after scores of
the launch post itself. If you re-render this after changing the tool, re-check
the numbers first -- a demo that lies about its own output would be a strange
thing for this project to ship.

No LaTeX anywhere: all type is Pango Text/MarkupText, so this renders with just
cairo + pango + ffmpeg.
"""

from manim import (
    Scene, Text, MarkupText, VGroup, Rectangle, RoundedRectangle, Line, Dot,
    Write, FadeIn, FadeOut, Transform, Create, GrowFromCenter,
    UP, DOWN, LEFT, RIGHT, ORIGIN, DEGREES,
    config, rate_functions, there_and_back, always_redraw, ValueTracker,
    Arc, Circle,
)
import numpy as np

# ---------------------------------------------------------------- palette

BG = "#0d1117"          # github dark, so the README embed sits flush
INK = "#e6edf3"
MUTED = "#7d8590"
GOOD = "#3fb950"
BAD = "#f85149"
WARN = "#d29922"
ACCENT = "#58a6ff"

MONO = "Menlo"
SANS = "Helvetica Neue"

config.background_color = BG


def mono(txt, size=28, color=INK, weight=None):
    kwargs = {"font": MONO, "font_size": size, "color": color}
    if weight:
        kwargs["weight"] = weight
    return Text(txt, **kwargs)


def sans(txt, size=34, color=INK, weight=None):
    kwargs = {"font": SANS, "font_size": size, "color": color}
    if weight:
        kwargs["weight"] = weight
    return Text(txt, **kwargs)


class Caption(VGroup):
    """
    Burned-in subtitles, fixed to the lower third.

    Burned in rather than a sidecar track because LinkedIn autoplays muted --
    an uncaptioned reel is a silent reel. The .srt is emitted separately for
    players that want real subtitles.
    """

    def __init__(self, text, size=30):
        super().__init__()
        self.label = sans(text, size=size, color=INK)
        self.label.to_edge(DOWN, buff=0.62)
        self.add(self.label)


class BeingHumanDemo(Scene):

    def caption(self, text, run=0.35):
        # Record the real render clock so the .srt matches the burned-in text
        # exactly. Hand-timed subtitles drift the moment any run_time changes.
        self._marks.append({"start": float(self.renderer.time), "text": text})
        new = Caption(text)
        if hasattr(self, "_cap") and self._cap is not None:
            self.play(FadeOut(self._cap, run_time=0.18),
                      FadeIn(new, run_time=run))
        else:
            self.play(FadeIn(new, run_time=run))
        self._cap = new

    def clear_caption(self):
        if self._marks:
            self._marks[-1]["end"] = float(self.renderer.time)
        if getattr(self, "_cap", None) is not None:
            self.play(FadeOut(self._cap, run_time=0.25))
            self._cap = None

    def construct(self):
        self._cap = None
        self._marks = []
        self.beat_problem()
        self.beat_why()
        self.beat_harvest()
        self.beat_voiceprint()
        self.beat_two_axes()
        self.beat_result()
        self.dump_marks()

    def dump_marks(self):
        """Write caption timings next to the scene, for srt generation."""
        import json
        import os
        end = float(self.renderer.time)
        for i, m in enumerate(self._marks):
            if "end" not in m:
                m["end"] = self._marks[i + 1]["start"] if i + 1 < len(self._marks) else end
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captions.json")
        with open(path, "w") as fh:
            json.dump({"duration": end, "cues": self._marks}, fh, indent=2)

    # ------------------------------------------------------------ 1. problem

    def beat_problem(self):
        slop = VGroup(
            sans("In today's fast-paced world,", size=30, color=MUTED),
            sans("let's delve into what makes", size=30, color=MUTED),
            sans("this a game-changer.", size=30, color=MUTED),
        ).arrange(DOWN, buff=0.28).shift(UP * 0.6)

        self.caption("every ai writing tool sounds the same.")
        for line in slop:
            self.play(Write(line, run_time=0.5))
        self.wait(0.5)

        strike = Line(
            slop.get_left() + LEFT * 0.15, slop.get_right() + RIGHT * 0.15,
            color=BAD, stroke_width=6,
        ).move_to(slop.get_center())
        self.play(Create(strike, run_time=0.5))
        self.wait(0.4)
        self.play(FadeOut(slop), FadeOut(strike), run_time=0.4)

    # ---------------------------------------------------------------- 2. why

    def beat_why(self):
        self.caption("the model has no idea who you are.")
        line1 = sans("so it writes the average", size=38).shift(UP * 0.9)
        line2 = sans("of everyone it ever read.", size=38).next_to(line1, DOWN, buff=0.3)
        self.play(FadeIn(line1, shift=UP * 0.2, run_time=0.5))
        self.play(FadeIn(line2, shift=UP * 0.2, run_time=0.5))
        self.wait(0.7)

        self.caption("there's only one fix. tell it.")
        self.play(FadeOut(line1), FadeOut(line2), run_time=0.4)
        # Hold: at 0.75s this cue was on screen too briefly to read.
        self.wait(0.9)

    # ------------------------------------------------------------ 3. harvest

    def beat_harvest(self):
        self.caption("it reads the prompts you already wrote.")

        prompts = [
            "fix the alignment, keep it short",
            "can you draft the abstract",
            "give me the codes for this",
            "there's still an error in the plot",
            "make the tone natural and human",
        ]
        rows = VGroup(*[
            mono(p, size=22, color=MUTED) for p in prompts
        ]).arrange(DOWN, buff=0.22, aligned_edge=LEFT).shift(UP * 0.7)

        for r in rows:
            self.play(FadeIn(r, shift=RIGHT * 0.25, run_time=0.22))
        self.wait(0.4)

        counter = VGroup(
            mono("1,187", size=54, color=ACCENT, weight="BOLD"),
            sans("messages", size=24, color=MUTED),
            mono("42,477", size=54, color=ACCENT, weight="BOLD"),
            sans("words", size=24, color=MUTED),
        ).arrange(DOWN, buff=0.1).shift(DOWN * 0.2)

        self.play(FadeOut(rows, run_time=0.35))
        self.play(FadeIn(counter, scale=1.08, run_time=0.6))
        self.wait(0.8)
        self.play(FadeOut(counter, run_time=0.4))

    # --------------------------------------------------------- 4. voiceprint

    def beat_voiceprint(self):
        self.caption("and turns it into instructions with numbers.")

        title = mono("voiceprint", size=30, color=MUTED).shift(UP * 2.3)

        facts = [
            ('lowercase "i"', "83%"),
            ("sentence length", "9 words, sd 8"),
            ("em dash", "1.3 / 1k"),
            ("exclamation", "0.28 / 1k"),
            ("hedging", "1.1 / 1k"),
        ]
        rows = VGroup()
        for k, v in facts:
            key = sans(k, size=27, color=MUTED)
            val = mono(v, size=27, color=INK)
            row = VGroup(key, val).arrange(RIGHT, buff=0.45)
            rows.add(row)
        rows.arrange(DOWN, buff=0.3, aligned_edge=LEFT).shift(UP * 0.55)
        for row in rows:
            row[1].align_to(rows, RIGHT)

        self.play(FadeIn(title, run_time=0.3))
        for row in rows:
            self.play(FadeIn(row, shift=RIGHT * 0.2, run_time=0.2))
        self.wait(0.6)

        self.caption('not "be concise". a number you can follow.')
        self.wait(0.9)
        self.play(FadeOut(rows), FadeOut(title), run_time=0.4)

    # ----------------------------------------------------------- 5. two axes

    def beat_two_axes(self):
        """
        The load-bearing beat. Generic slop PASSES the authorship check and
        fails the slop check; a different person's clean prose does the exact
        reverse. One gauge each, shown failing in opposite directions, is the
        clearest way to show why one number was never enough.
        """
        self.caption("then it checks a draft twice.")
        self.wait(0.35)

        left = self.gauge("ai tells", LEFT * 1.85 + UP * 0.55)
        right = self.gauge("is it you", RIGHT * 1.85 + UP * 0.55)
        self.play(FadeIn(left["group"]), FadeIn(right["group"]), run_time=0.5)
        self.wait(0.4)

        # generic slop: fails tells, passes authorship
        self.caption("generic ai text: caught by one, missed by the other.")
        self.set_gauge(left, 31, BAD)
        self.set_gauge(right, 30, GOOD)
        self.wait(1.1)

        # someone else's clean prose: the reverse
        self.caption("someone else's clean writing: the exact reverse.")
        self.set_gauge(left, 97, GOOD)
        self.set_gauge(right, 94, BAD)
        self.wait(1.2)

        self.caption("neither test catches both. so it runs both.")
        self.wait(1.0)
        self.play(FadeOut(left["group"]), FadeOut(right["group"]), run_time=0.4)

    def gauge(self, label, pos):
        ring = Circle(radius=1.0, stroke_color=MUTED, stroke_width=6, fill_opacity=0)
        num = mono("--", size=44, color=MUTED)
        cap = sans(label, size=25, color=MUTED)
        cap.next_to(ring, DOWN, buff=0.28)
        num.move_to(ring.get_center())
        group = VGroup(ring, num, cap).move_to(pos)
        return {"group": group, "ring": ring, "num": num, "cap": cap}

    def set_gauge(self, g, value, color):
        new_num = mono(str(value), size=44, color=color).move_to(g["ring"].get_center())
        new_ring = Circle(
            radius=1.0, stroke_color=color, stroke_width=8, fill_opacity=0
        ).move_to(g["ring"].get_center())
        self.play(
            Transform(g["num"], new_num),
            Transform(g["ring"], new_ring),
            run_time=0.45,
        )

    # -------------------------------------------------------------- 6. result

    def beat_result(self):
        self.caption("this post scored 31 before. 95 after.")

        before = VGroup(
            mono("31", size=76, color=BAD, weight="BOLD"),
            sans("first draft", size=24, color=MUTED),
        ).arrange(DOWN, buff=0.14).shift(LEFT * 1.9 + UP * 0.6)

        arrow = sans("->", size=44, color=MUTED).shift(UP * 0.75)

        after = VGroup(
            mono("95", size=76, color=GOOD, weight="BOLD"),
            sans("after being-human", size=24, color=MUTED),
        ).arrange(DOWN, buff=0.14).shift(RIGHT * 1.9 + UP * 0.6)

        self.play(FadeIn(before, run_time=0.45))
        self.play(FadeIn(arrow, run_time=0.25))
        self.play(FadeIn(after, scale=1.1, run_time=0.5))
        self.wait(1.1)

        self.clear_caption()
        self.play(FadeOut(before), FadeOut(arrow), FadeOut(after), run_time=0.4)

        name = sans("being-human", size=62, color=INK, weight="BOLD").shift(UP * 0.75)
        tag = sans("write like you, not like a press release",
                   size=27, color=MUTED).next_to(name, DOWN, buff=0.3)
        install = mono("pip install being-human", size=27, color=ACCENT)
        install.next_to(tag, DOWN, buff=0.55)
        repo = mono("github.com/Syedomershah99/being-human",
                    size=21, color=MUTED).next_to(install, DOWN, buff=0.3)

        self.play(FadeIn(name, shift=UP * 0.2, run_time=0.6))
        self.play(FadeIn(tag, run_time=0.4))
        self.play(FadeIn(install, run_time=0.4))
        self.play(FadeIn(repo, run_time=0.35))
        self.wait(1.8)
        self.play(FadeOut(VGroup(name, tag, install, repo), run_time=0.7))
        self.wait(0.4)
