from manim import *
import numpy as np


class Animation(Scene):
    def setup_layout(
        self,
        show_alice=True,
        show_mitm=True,
        show_bob=True,
        show_ca=True,
        show_ab_links=True,
        show_ca_links=False,
    ):
        # Fixed anchor positions
        self.actor_points = {
            "alice": LEFT * 4,
            "mitm": ORIGIN,
            "bob": RIGHT * 4,
            "ca": UP * 3,
        }

        self.actors = {}  # name -> VGroup(box, text)
        self.actor_boxes = {}  # name -> box

        if show_alice:
            self.actors["alice"] = self._make_actor("Alice", self.actor_points["alice"])
        if show_mitm:
            self.actors["mitm"] = self._make_actor("MITM", self.actor_points["mitm"])
        if show_bob:
            self.actors["bob"] = self._make_actor("Bob", self.actor_points["bob"])
        if show_ca:
            self.actors["ca"] = self._make_actor("CA", self.actor_points["ca"])

        self.links = {}

        if show_ab_links:
            if "alice" in self.actors and "mitm" in self.actors:
                self.links["alice_mitm"] = self._make_link("alice", "mitm")
            if "mitm" in self.actors and "bob" in self.actors:
                self.links["mitm_bob"] = self._make_link("mitm", "bob")

        if show_ca_links:
            if "alice" in self.actors and "ca" in self.actors:
                self.links["alice_ca"] = self._make_link("alice", "ca")
            if "bob" in self.actors and "ca" in self.actors:
                self.links["bob_ca"] = self._make_link("bob", "ca")

        self.add(
            *[v for v in self.actors.values()],
            *[v for v in self.links.values()],
        )

    def _make_actor(self, label, point):
        # Text label
        text = Text(label).scale(0.7)

        # Box that hugs the text, nice and simple
        box = SurroundingRectangle(text, buff=0.3)

        # Group and move to desired position
        group = VGroup(box, text)
        group.move_to(point)

        # Store box for edge-to-edge lines
        name = label.lower() if label != "MITM" else "mitm"
        self.actor_boxes[name] = box

        return group

    def _make_link(self, actor_a, actor_b):
        box_a = self.actor_boxes[actor_a]
        box_b = self.actor_boxes[actor_b]

        direction = box_b.get_center() - box_a.get_center()
        direction = direction / np.linalg.norm(direction)

        start = box_a.get_boundary_point(direction)
        end = box_b.get_boundary_point(-direction)

        return Line(start, end)

    def _slot_point(self, actor_name, slot="right"):
        base = self.actor_boxes[actor_name].get_center()
        offset = {
            "right": RIGHT * 1.8,
            "left": LEFT * 1.8,
            "above": UP * 1.5,
            "below": DOWN * 1.5,
        }.get(slot, ORIGIN)
        return base + offset

    def make_payload(self, actor_name, slot="right", label="m"):
        pos = self._slot_point(actor_name, slot)
        rect = RoundedRectangle(
            corner_radius=0.15,
            width=1.2,
            height=0.6,
            stroke_width=2,
        )
        rect.move_to(pos)
        txt = Text(label).scale(0.45)
        txt.move_to(rect.get_center())
        payload = VGroup(rect, txt)
        self.add(payload)
        return payload

    def construct(self):
        # Base layout: Alice - MITM - Bob with CA on top
        self.setup_layout(
            show_alice=True,
            show_mitm=True,
            show_bob=True,
            show_ca=True,
            show_ab_links=True,
            show_ca_links=True,
        )

        self.wait(0.5)

        # DH1 payload: starts below Alice
        dh1 = self.make_payload("alice", slot="below", label="DH1")
        self.wait(0.5)

        # Path under the bottom line: Alice -> MITM (pause) -> Bob (rest under Bob)
        start = self._slot_point("alice", "below")
        mid = self._slot_point("mitm", "below")
        end = self._slot_point("bob", "below")

        self.play(MoveAlongPath(dh1, Line(start, mid)), run_time=2)
        self.wait(0.5)
        self.play(MoveAlongPath(dh1, Line(mid, end)), run_time=2)
        self.wait(1)
