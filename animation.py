from manim import *
import numpy as np


class NetworkScene(MovingCameraScene):
    def setup_layout(
        self,
        show_alice=True,
        show_mitm=True,
        show_bob=True,
        show_ca=True,
        show_ab_links=True,
        show_ca_links=True,
        animate_actors=None,
        animate_links=None,
    ):
        """
        Create the base network layout: actors (Alice, MITM, Bob, CA) and links between them.

        Actors/links can either be added to the scene immediately or queued to be animated in later.
        """
        animate_actors = set(animate_actors or [])
        animate_links = set(animate_links or [])

        self.actor_points = {
            "alice": LEFT * 4,
            "mitm": ORIGIN,
            "bob": RIGHT * 4,
            "ca": UP * 3,
        }

        self.actors = {}
        self.actor_boxes = {}
        self.links = {}

        # Keep track of which elements should be animated in later
        self.actors_to_animate = []
        self.links_to_animate = []

        if show_alice:
            self.actors["alice"] = self._make_actor("Alice", self.actor_points["alice"])
        if show_mitm:
            self.actors["mitm"] = self._make_actor("MITM", self.actor_points["mitm"])
        if show_bob:
            self.actors["bob"] = self._make_actor("Bob", self.actor_points["bob"])
        if show_ca:
            self.actors["ca"] = self._make_actor("CA", self.actor_points["ca"])

        # Decide which actors are static vs animated
        actors_to_add = []
        for name, actor in self.actors.items():
            if name in animate_actors:
                self.actors_to_animate.append(actor)
            else:
                actors_to_add.append(actor)

        if show_ab_links:
            # Alice <-> MITM
            if "alice" in self.actors and "mitm" in self.actors:
                self.links["alice_mitm"] = self._make_link("alice", "mitm")

            # MITM <-> Bob
            if "mitm" in self.actors and "bob" in self.actors:
                self.links["mitm_bob"] = self._make_link("mitm", "bob")

            # Direct Alice <-> Bob only when there is no MITM
            if (
                "alice" in self.actors
                and "bob" in self.actors
                and "mitm" not in self.actors
            ):
                self.links["alice_bob"] = self._make_link("alice", "bob")

        if show_ca_links:
            if "alice" in self.actors and "ca" in self.actors:
                self.links["alice_ca"] = self._make_link("alice", "ca")
            if "bob" in self.actors and "ca" in self.actors:
                self.links["bob_ca"] = self._make_link("bob", "ca")

        # Decide which links are static vs animated
        links_to_add = []
        for name, link in self.links.items():
            if name in animate_links:
                self.links_to_animate.append(link)
            else:
                links_to_add.append(link)

        # Add elements that should be present from the start
        self.add(*actors_to_add, *links_to_add)

    def animate_entrance(self, run_time=0.8):
        """
        Animate in actors and links that were flagged for animation in setup_layout.

        Actors fade in with a slight upward shift; links are drawn with Create.
        """
        actor_anims = [
            FadeIn(actor, shift=UP * 0.3) for actor in self.actors_to_animate
        ]
        link_anims = [Create(link) for link in self.links_to_animate]

        for anim in actor_anims:
            self.play(anim, run_time=run_time)

        if link_anims:
            self.play(*link_anims, run_time=run_time)

    def _make_actor(self, label, point):
        """
        Build a labelled box for an actor and register its rectangle in actor_boxes.
        """
        text = Text(label).scale(0.7)
        color_dict = {
            "Alice": GREEN,
            "MITM": RED,
            "Bob": BLUE,
            "CA": YELLOW,
        }
        box = SurroundingRectangle(
            text, buff=0.3, color=color_dict[label], stroke_width=3
        )
        group = VGroup(box, text).move_to(point)

        name = label.lower() if label != "MITM" else "mitm"
        self.actor_boxes[name] = box
        return group

    def _make_link(self, actor_a, actor_b):
        """
        Construct a line between two actor boxes, with special handling for bottom and CA links.
        """
        box_a = self.actor_boxes[actor_a]
        box_b = self.actor_boxes[actor_b]

        # Bottom horizontal line (Alice/MITM/Bob)
        if {actor_a, actor_b} <= {"alice", "mitm", "bob"}:
            if box_a.get_center()[0] < box_b.get_center()[0]:
                start = box_a.get_right()
                end = box_b.get_left()
            else:
                start = box_b.get_right()
                end = box_a.get_left()
            return Line(start, end)

        # Slanted lines to CA
        if actor_a == "ca":
            ca_box, other_box = box_a, box_b
        elif actor_b == "ca":
            ca_box, other_box = box_b, box_a
        else:
            ca_box, other_box = None, None

        if ca_box is not None:
            other_center = other_box.get_center()
            ca_center = ca_box.get_center()
            if other_center[0] < ca_center[0]:
                ca_target = ca_box.get_left()
            else:
                ca_target = ca_box.get_right()
            start = other_box.get_top()
            end = ca_target
            return Line(start, end)

        # Generic line between two boxes if nothing special applies
        direction = box_b.get_center() - box_a.get_center()
        direction = direction / np.linalg.norm(direction)
        start = box_a.get_boundary_point(direction)
        end = box_b.get_boundary_point(-direction)
        return Line(start, end)

    def _offset_path(self, base_start, base_end, offset=1.0, shorten_factor=0.2):
        """
        Build a path parallel to a base segment, shifted sideways and slightly shortened.
        """
        v = base_end - base_start
        length = np.linalg.norm(v)
        direction = v / length

        perp = np.array([-direction[1], direction[0], 0.0])
        perp = perp / np.linalg.norm(perp)

        start = base_start + perp * offset
        end = base_end + perp * offset - direction * (length * shorten_factor)
        return Line(start, end)

    def build_ca_paths(self):
        """
        Build offset paths between Alice/Bob and the CA for packets that travel via CA lanes.
        """
        if not {"alice", "bob", "ca"} <= self.actor_boxes.keys():
            return

        alice_box = self.actor_boxes["alice"]
        bob_box = self.actor_boxes["bob"]
        ca_box = self.actor_boxes["ca"]

        alice_link_start = alice_box.get_top()
        alice_link_end = ca_box.get_left()

        bob_link_start = bob_box.get_top()
        bob_link_end = ca_box.get_right()

        self.alice_to_ca_path = self._offset_path(
            alice_link_start, alice_link_end, offset=1.0, shorten_factor=0.25
        )
        self.ca_to_alice_path = Line(
            self.alice_to_ca_path.get_end(), self.alice_to_ca_path.get_start()
        )

        self.bob_to_ca_path = self._offset_path(
            bob_link_start, bob_link_end, offset=1.0, shorten_factor=0.25
        )
        self.ca_to_bob_path = Line(
            self.bob_to_ca_path.get_end(), self.bob_to_ca_path.get_start()
        )

    def _downshift_line(self, line, offset=1.5):
        """
        Return a copy of a line shifted straight down by a fixed offset.
        """
        return Line(
            line.get_start() + DOWN * offset,
            line.get_end() + DOWN * offset,
        )

    def build_ab_paths(self, offset_down=1.5):
        """
        Define separate bottom paths for Alice↔MITM, MITM↔Bob, and Alice↔Bob (if direct).

        These are used for packets that travel along a dedicated horizontal lane under the actors.
        """
        offset_vec = DOWN * offset_down
        boxes = self.actor_boxes

        # Alice ↔ MITM
        if "alice" in boxes and "mitm" in boxes:
            alice_point = boxes["alice"].get_bottom() + offset_vec
            mitm_point = boxes["mitm"].get_bottom() + offset_vec

            self.alice_to_mitm_path = Line(alice_point, mitm_point)
            self.mitm_to_alice_path = Line(mitm_point, alice_point)

        # MITM ↔ Bob
        if "mitm" in boxes and "bob" in boxes:
            mitm_point = boxes["mitm"].get_bottom() + offset_vec
            bob_point = boxes["bob"].get_bottom() + offset_vec

            self.mitm_to_bob_path = Line(mitm_point, bob_point)
            self.bob_to_mitm_path = Line(bob_point, mitm_point)

        # Alice ↔ Bob (direct)
        if "alice" in boxes and "bob" in boxes and "mitm" not in boxes:
            alice_point = boxes["alice"].get_bottom() + offset_vec
            bob_point = boxes["bob"].get_bottom() + offset_vec

            self.alice_to_bob_path = Line(alice_point, bob_point)
            self.bob_to_alice_path = Line(bob_point, alice_point)

    def make_packet_at(self, point, label=None):
        """
        Create a square 'packet' at the given point, optionally with a text label, and add it to the scene.
        """
        sq = Square(
            side_length=0.6,
            fill_color=RED,
            fill_opacity=1.0,
            stroke_width=0,
        ).move_to(point)
        if label:
            txt = Text(label).scale(0.4).move_to(sq.get_center())
            grp = VGroup(sq, txt)
        else:
            grp = VGroup(sq)
        self.add(grp)
        return grp

    def spawn_payload_at(self, payload, point, run_time=1, entrance_anim=None):
        """
        Place a payload Mobject at a point and bring it on screen with a simple entrance animation.

        If the payload is text/MathTex, it is written; otherwise a small fade-and-grow is used by default.
        """
        payload.move_to(point)

        if isinstance(payload, MathTex) or isinstance(payload, Text):
            self.play(Write(payload), run_time=run_time)
            return payload

        if entrance_anim is None:
            entrance_anim = FadeIn(payload, scale=0.8, shift=UP * 0.1)

        self.play(entrance_anim, run_time=run_time)
        return payload

    def move_payload_along_path(self, payload, path, run_time=2, pause_after=0):
        """
        Move an existing payload along a given path, optionally pausing at the end.
        """
        self.play(MoveAlongPath(payload, path), run_time=run_time)
        if pause_after > 0:
            self.wait(pause_after)
        return payload

    def render_scratchpad(
        self,
        actor_name: str,
        title_text: str,
        items,
        buff: float = 1.0,
        panel_color=YELLOW,
        left_shift=0,
        down_shift=0,
        delays=[],
    ):
        """
        Render a labelled 'scratchpad' card above an actor and animate its contents in.

        The items argument should be a list of pre-built Mobjects (Text/MathTex) that will be written in order.
        """
        actor_box = self.actor_boxes[actor_name]

        title = Text(title_text, font_size=28)

        # Column of provided items (MathTex/Text), left-aligned
        column = VGroup(*items).arrange(DOWN, aligned_edge=LEFT, buff=0.15)

        # Title above column
        content = VGroup(title, column).arrange(DOWN, buff=0.25, aligned_edge=LEFT)

        panel = SurroundingRectangle(
            content,
            buff=0.3,
            color=panel_color,
            corner_radius=0.15,
            stroke_width=2,
        )

        card = VGroup(panel, content)

        # Position card roughly above the actor and allow a small tweak with shifts
        card.next_to(actor_box, UP, buff=buff)
        card.move_to(np.array([actor_box.get_center()[0], card.get_center()[1], 0.0]))
        card.shift(LEFT * left_shift)
        card.shift(DOWN * down_shift)

        # Animate card and entries in
        self.play(FadeIn(panel, shift=UP * 0.1, scale=0.95), run_time=0.4)
        self.play(Write(title), run_time=0.4)

        anim_time = 0.4
        for i, obj in enumerate(items):
            if len(delays) > i:
                self.wait(delays[i])
            else:
                self.wait(0.1)
            self.play(Write(obj), run_time=anim_time)

        return card


class Intro(Scene):
    def construct(self):
        """
        Title slide for the Diffie–Hellman animation sequence.
        """
        heading = Text(
            "Diffie-Hellman Key Exchange",
        )
        self.play(Write(heading))

        self.wait(0.4)

        name = Text("By Hugo Mainland", font_size=28).move_to(DOWN)
        self.play(Write(name))
        self.wait(1)


class DH0(NetworkScene):
    def construct(self):
        """
        Simple plaintext conversation: Alice talks directly to Bob with no MITM or CA.
        """
        self.setup_layout(
            show_alice=True,
            show_mitm=False,
            show_bob=True,
            show_ca=False,
            show_ab_links=True,
            show_ca_links=False,
            animate_actors=["alice", "bob"],
            animate_links=["alice_bob"],
        )

        self.animate_entrance(run_time=0.8)

        self.build_ab_paths(offset_down=1.5)

        self.wait(3)

        # Alice → Bob: "Morning Bob"
        msg_to_bob = Text("Morning Bob", font_size=32)

        self.spawn_payload_at(
            msg_to_bob,
            self.alice_to_bob_path.get_start(),
            run_time=0.6,
        )

        self.play(MoveAlongPath(msg_to_bob, self.alice_to_bob_path), run_time=2.0)
        self.wait(0.3)

        self.play(FadeOut(msg_to_bob), run_time=0.4)
        self.wait(0.2)

        # Bob → Alice: "Hi Alice"
        msg_to_alice = Text("Hi Alice", font_size=32)

        self.spawn_payload_at(
            msg_to_alice,
            self.bob_to_alice_path.get_start(),
            run_time=0.6,
        )

        self.play(MoveAlongPath(msg_to_alice, self.bob_to_alice_path), run_time=2.0)

        self.wait(1.0)


class DH1(NetworkScene):
    def construct(self):
        """
        Show how a MITM can silently relay a sensitive plaintext message between Alice and Bob.
        """
        self.setup_layout(
            show_alice=True,
            show_mitm=True,
            show_bob=True,
            show_ca=False,
            show_ab_links=True,
            show_ca_links=False,
            animate_actors=["mitm"],
            animate_links=["alice_mitm", "mitm_bob"],
        )

        self.build_ab_paths(offset_down=1.5)

        self.wait(0.3)

        self.animate_entrance(run_time=0.8)

        self.wait(27)

        # Alice → MITM → Bob: "What's your pin?"
        msg_to_bob = Text("What's your pin?", font_size=30)

        self.spawn_payload_at(
            msg_to_bob,
            self.alice_to_mitm_path.get_start(),
            run_time=0.6,
        )

        self.play(MoveAlongPath(msg_to_bob, self.alice_to_mitm_path), run_time=2.0)
        self.wait(0.4)

        self.play(MoveAlongPath(msg_to_bob, self.mitm_to_bob_path), run_time=2.0)
        self.wait(0.3)

        self.play(FadeOut(msg_to_bob), run_time=0.4)
        self.wait(0.2)

        # Bob → MITM → Alice: "It's 4293"
        reply = Text("It's 4293", font_size=30)

        self.spawn_payload_at(
            reply,
            self.bob_to_mitm_path.get_start(),
            run_time=0.6,
        )

        self.play(MoveAlongPath(reply, self.bob_to_mitm_path), run_time=2.0)
        self.wait(0.4)

        self.play(MoveAlongPath(reply, self.mitm_to_alice_path), run_time=2.0)

        self.wait(1.0)


class DH2pre(NetworkScene):
    def construct(self):
        """
        Generic algebraic Diffie–Hellman example: MITM observes public values and the flow of A and B.
        """
        self.setup_layout(
            show_alice=True,
            show_mitm=True,
            show_bob=True,
            show_ca=False,
            show_ab_links=True,
            show_ca_links=False,
        )

        self.wait(0.3)

        # 1) Alice's scratchpad above her: p, α, x, A = α^x mod p
        p_sp = MathTex(r"p", font_size=30)
        alpha_sp = MathTex(r"\alpha", font_size=30)
        x_sp = MathTex(r"x", font_size=30)
        A_sp = MathTex(r"A = \alpha^x \bmod p", font_size=30)

        B_sp = MathTex(r"B = \alpha^y \bmod p", font_size=30)
        B_sp.set_opacity(0)
        B_sp.set_stroke(opacity=0)

        K_sp = MathTex(r"K = B^x \bmod p", font_size=30)
        K_sp.set_opacity(0)
        K_sp.set_stroke(opacity(0))

        self.render_scratchpad(
            actor_name="alice",
            title_text="Alice's DH values",
            items=[
                p_sp,
                alpha_sp,
                x_sp,
                A_sp,
                B_sp,
                K_sp,
            ],
            buff=0.2,
            delays=[2, 2.4, 6.2, 3.9],
        )

        self.wait(5)

        # 2) Build bottom paths: Alice ↔ MITM ↔ Bob
        self.build_ab_paths(offset_down=1.5)

        base_a2m = self.alice_to_mitm_path
        base_m2b = self.mitm_to_bob_path

        vertical_offsets = [UP * 0.4, ORIGIN, DOWN * 0.4]

        # 3) p, α, A appear under Alice, stacked, then go to MITM
        p_move = MathTex(r"p", font_size=34)
        alpha_move = MathTex(r"\alpha", font_size=34)
        A_move = MathTex(r"A = \alpha^x \bmod p", font_size=34)

        moving_values = [p_move, alpha_move, A_move]

        paths_a2m = []
        paths_m2b = []

        for offset in vertical_offsets:
            paths_a2m.append(base_a2m.copy().shift(offset))
            paths_m2b.append(base_m2b.copy().shift(offset))

        for val, path in zip(moving_values, paths_a2m):
            self.spawn_payload_at(val, path.get_start(), run_time=0.4)

        self.wait(0.2)

        self.play(
            LaggedStart(
                *[
                    MoveAlongPath(val, path)
                    for val, path in zip(moving_values, paths_a2m)
                ],
                lag_ratio=0.05,
                run_time=2.0,
            )
        )

        # 4) MITM's "Public values" scratchpad
        p_pub = MathTex(r"p", font_size=34)
        alpha_pub = MathTex(r"\alpha", font_size=34)
        A_pub = MathTex(r"A = \alpha^x \bmod p", font_size=34)

        B_pub = MathTex(r"B = \alpha^y \bmod p", font_size=34)
        B_pub.set_opacity(0)
        B_pub.set_stroke(opacity=0)

        self.render_scratchpad(
            actor_name="mitm",
            title_text="Public values",
            items=[p_pub, alpha_pub, A_pub, B_pub],
            buff=0.2,
        )

        # 5) Move p, α, A under MITM over to Bob
        mitm_values = [p_move, alpha_move, A_move]

        self.play(
            LaggedStart(
                *[
                    MoveAlongPath(val, path)
                    for val, path in zip(mitm_values, paths_m2b)
                ],
                lag_ratio=0.05,
                run_time=1.2,
            )
        )

        # 6) Bob's scratchpad with his DH values
        p_bob = MathTex(r"p", font_size=30)
        alpha_bob = MathTex(r"\alpha", font_size=30)
        y_bob = MathTex(r"y", font_size=30)
        A_bob = MathTex(r"A = \alpha^x \bmod p", font_size=30)
        B_bob = MathTex(r"B = \alpha^y \bmod p", font_size=30)
        K_bob = MathTex(r"K = A^y \bmod p", font_size=30)

        self.render_scratchpad(
            actor_name="bob",
            title_text="Bob's DH values",
            items=[p_bob, alpha_bob, y_bob, A_bob, B_bob, K_bob],
            buff=0.2,
            delays=[2.4, 0.7, 2.6, 2.7, 3.8, 4.5],
        )

        self.wait(5)

        # 7) Replace values under Bob with B, send B back to MITM
        self.play(
            FadeOut(p_move),
            FadeOut(alpha_move),
            FadeOut(A_move),
            run_time=0.5,
        )
        self.wait(0.5)

        B_move = MathTex(r"B = \alpha^y \bmod p", font_size=34)

        bob_to_mitm_path = self.bob_to_mitm_path

        self.spawn_payload_at(
            B_move,
            bob_to_mitm_path.get_start(),
            run_time=0.4,
        )

        self.play(MoveAlongPath(B_move, bob_to_mitm_path), run_time=2.0)
        self.wait(0.4)

        # 8) Reveal B in MITM's scratchpad, then send B to Alice
        self.play(
            B_pub.animate.set_opacity(1).set_stroke(opacity=1),
            run_time=0.6,
        )
        self.wait(0.4)

        mitm_to_alice_path = self.mitm_to_alice_path

        self.play(MoveAlongPath(B_move, mitm_to_alice_path), run_time=2.0)
        self.wait(0.4)

        # 9) Alice stores B and K in her scratchpad (unhide rows)
        self.play(
            B_sp.animate.set_opacity(1).set_stroke(opacity=1),
            run_time=0.6,
        )
        self.wait(0.2)

        self.play(
            K_sp.animate.set_opacity(1).set_stroke(opacity=1),
            run_time=0.6,
        )
        self.wait(0.4)

        self.play(FadeOut(B_move), run_time=0.4)

        self.wait(1.0)

        # 10) Pull out K from Alice and Bob, show algebra and discrete log problem
        K_alice_global = K_sp.copy()
        K_bob_global = K_bob.copy()

        K_alice_global.move_to(K_sp.get_center())
        K_bob_global.move_to(K_bob.get_center())

        self.add(K_alice_global, K_bob_global)

        temp_group = VGroup(
            K_alice_global.copy(),
            K_bob_global.copy(),
        ).arrange(DOWN, buff=0.3)
        temp_group.move_to(DOWN * 1.8)

        target_pos_alice = temp_group[0].get_center()
        target_pos_bob = temp_group[1].get_center()

        scale_factor = 36 / 34

        self.play(
            K_alice_global.animate.move_to(target_pos_alice).scale(scale_factor),
            K_bob_global.animate.move_to(target_pos_bob).scale(scale_factor),
            run_time=1.5,
        )
        self.wait(0.5)

        k1_step1 = MathTex(
            r"K = (\alpha^y \bmod p)^x \bmod p",
            font_size=36,
        ).move_to(K_alice_global.get_center())

        k2_step1 = MathTex(
            r"K = (\alpha^x \bmod p)^y \bmod p",
            font_size=36,
        ).move_to(K_bob_global.get_center())

        self.play(Transform(K_alice_global, k1_step1), run_time=1.0)
        self.play(Transform(K_bob_global, k2_step1), run_time=1.0)
        self.wait(0.5)

        k1_step2 = MathTex(
            r"K = (\alpha^y)^x \bmod p",
            font_size=36,
        ).move_to(K_alice_global.get_center())

        k2_step2 = MathTex(
            r"K = (\alpha^x)^y \bmod p",
            font_size=36,
        ).move_to(K_bob_global.get_center())

        self.play(Transform(K_alice_global, k1_step2), run_time=1.0)
        self.play(Transform(K_bob_global, k2_step2), run_time=1.0)
        self.wait(0.5)

        k_final_top = MathTex(
            r"K = \alpha^{xy} \bmod p",
            font_size=36,
        ).move_to(K_alice_global.get_center())

        k_final_bottom = MathTex(
            r"K = \alpha^{xy} \bmod p",
            font_size=36,
        ).move_to(K_bob_global.get_center())

        self.play(Transform(K_alice_global, k_final_top), run_time=1.0)
        self.play(Transform(K_bob_global, k_final_bottom), run_time=1.0)

        self.wait(1.0)

        final_center = (K_alice_global.get_center() + K_bob_global.get_center()) / 2

        self.play(
            FadeOut(K_alice_global),
            FadeOut(K_bob_global),
            run_time=0.6,
        )

        dlp_line = MathTex(
            r"\text{Find } x \text{ such that } \alpha^x \equiv A \pmod p",
            font_size=36,
        )
        dlp_line.move_to(final_center)

        self.play(Write(dlp_line), run_time=1.2)
        self.wait(1.0)


class DH2(NetworkScene):
    def construct(self):
        """
        Concrete Diffie–Hellman example with small numbers (p=7, α=3) to show the full flow.
        """
        self.camera.frame.shift(UP * 0.2)

        self.setup_layout(
            show_alice=True,
            show_mitm=True,
            show_bob=True,
            show_ca=False,
            show_ab_links=True,
            show_ca_links=False,
        )

        self.wait(0.3)

        # 1) Alice's concrete DH values
        p_sp = MathTex(r"p = 7", font_size=30)
        alpha_sp = MathTex(r"\alpha = 3", font_size=30)
        x_sp = MathTex(r"x = 2", font_size=30)
        A_sp = MathTex(r"A = 3^2 \bmod 7 = 2", font_size=30)

        B_sp = MathTex(r"B = 5", font_size=30)
        B_sp.set_opacity(0)
        B_sp.set_stroke(opacity=0)

        K_sp = MathTex(r"K = 5^2 \bmod 7 = 4", font_size=30)
        K_sp.set_opacity(0)
        K_sp.set_stroke(opacity=0)

        self.render_scratchpad(
            actor_name="alice",
            title_text="Alice's DH values",
            items=[p_sp, alpha_sp, x_sp, A_sp, B_sp, K_sp],
            buff=0.2,
        )

        self.wait(0.5)

        # 2) Paths Alice ↔ MITM ↔ Bob
        self.build_ab_paths(offset_down=1.5)

        base_a2m = self.alice_to_mitm_path
        base_m2b = self.mitm_to_bob_path

        vertical_offsets = [UP * 0.4, ORIGIN, DOWN * 0.4]

        # 3) p, α, A under Alice → MITM
        p_move = MathTex(r"p = 7", font_size=34)
        alpha_move = MathTex(r"\alpha = 3", font_size=34)
        A_move = MathTex(r"A = 2", font_size=34)

        moving_values = [p_move, alpha_move, A_move]

        paths_a2m = []
        paths_m2b = []

        for offset in vertical_offsets:
            paths_a2m.append(base_a2m.copy().shift(offset))
            paths_m2b.append(base_m2b.copy().shift(offset))

        for val, path in zip(moving_values, paths_a2m):
            self.spawn_payload_at(val, path.get_start(), run_time=0.4)

        self.wait(0.2)

        self.play(
            LaggedStart(
                *[
                    MoveAlongPath(val, path)
                    for val, path in zip(moving_values, paths_a2m)
                ],
                lag_ratio=0.05,
                run_time=2.0,
            )
        )

        self.wait(0.4)

        # 4) MITM's public-values scratchpad (concrete)
        p_pub = MathTex(r"p = 7", font_size=34)
        alpha_pub = MathTex(r"\alpha = 3", font_size=34)
        A_pub = MathTex(r"A = 2", font_size=34)

        B_pub = MathTex(r"B = 5", font_size=34)
        B_pub.set_opacity(0)
        B_pub.set_stroke(opacity=0)

        self.render_scratchpad(
            actor_name="mitm",
            title_text="Public values",
            items=[p_pub, alpha_pub, A_pub, B_pub],
            buff=0.2,
        )

        self.wait(0.5)

        # 5) Move values under MITM to Bob
        mitm_values = [p_move, alpha_move, A_move]

        self.play(
            LaggedStart(
                *[
                    MoveAlongPath(val, path)
                    for val, path in zip(mitm_values, paths_m2b)
                ],
                lag_ratio=0.05,
                run_time=2.0,
            )
        )

        self.wait(1.0)

        # 6) Bob computes his side of DH
        p_bob = MathTex(r"p = 7", font_size=30)
        alpha_bob = MathTex(r"\alpha = 3", font_size=30)
        y_bob = MathTex(r"y = 5", font_size=30)
        A_bob = MathTex(r"A = 2", font_size=30)
        B_bob = MathTex(r"B = 3^5 \bmod 7 = 5", font_size=30)
        K_bob = MathTex(r"K = 2^5 \bmod 7 = 4", font_size=30)

        self.render_scratchpad(
            actor_name="bob",
            title_text="Bob's DH values",
            items=[p_bob, alpha_bob, y_bob, A_bob, B_bob, K_bob],
            buff=0.2,
        )

        self.wait(1.0)

        # 7) Bob sends B back via MITM
        self.play(
            FadeOut(p_move),
            FadeOut(alpha_move),
            FadeOut(A_move),
            run_time=0.5,
        )
        self.wait(0.2)

        B_move = MathTex(r"B = 5", font_size=34)

        bob_to_mitm_path = self.bob_to_mitm_path

        self.spawn_payload_at(
            B_move,
            bob_to_mitm_path.get_start(),
            run_time=0.4,
        )

        self.play(MoveAlongPath(B_move, bob_to_mitm_path), run_time=2.0)
        self.wait(0.4)

        # 8) Reveal B in MITM's scratchpad, then forward to Alice
        self.play(
            B_pub.animate.set_opacity(1).set_stroke(opacity=1),
            run_time=0.6,
        )
        self.wait(0.4)

        mitm_to_alice_path = self.mitm_to_alice_path

        self.play(MoveAlongPath(B_move, mitm_to_alice_path), run_time=2.0)
        self.wait(0.4)

        # 9) Alice fills in B and K in her card
        self.play(
            B_sp.animate.set_opacity(1).set_stroke(opacity=1),
            run_time=0.6,
        )
        self.wait(0.2)

        self.play(
            K_sp.animate.set_opacity(1).set_stroke(opacity=1),
            run_time=0.6,
        )
        self.wait(0.4)

        self.play(FadeOut(B_move), run_time=0.4)

        self.wait(1.0)


class DH3(NetworkScene):
    def construct(self):
        """
        Demonstrate how a MITM can brute-force Alice's small exponent x once p, α and A are known.
        """
        self.camera.frame.shift(UP * 0.2)

        self.setup_layout(
            show_alice=True,
            show_mitm=True,
            show_bob=True,
            show_ca=False,
            show_ab_links=True,
            show_ca_links=False,
        )

        self.wait(0.3)

        # 1) Build bottom paths for the DH values
        self.build_ab_paths(offset_down=1.5)

        base_a2m = self.alice_to_mitm_path
        base_m2b = self.mitm_to_bob_path

        vertical_offsets = [UP * 0.4, ORIGIN, DOWN * 0.4]

        # 2) p, α, A under Alice → MITM
        p_move = MathTex(r"p = 7", font_size=34)
        alpha_move = MathTex(r"\alpha = 3", font_size=34)
        A_move = MathTex(r"A = 2", font_size=34)

        moving_values = [p_move, alpha_move, A_move]

        paths_a2m = []
        paths_m2b = []

        for offset in vertical_offsets:
            paths_a2m.append(base_a2m.copy().shift(offset))
            paths_m2b.append(base_m2b.copy().shift(offset))

        for val, path in zip(moving_values, paths_a2m):
            self.spawn_payload_at(val, path.get_start(), run_time=0.4)

        self.wait(0.2)

        self.play(
            LaggedStart(
                *[
                    MoveAlongPath(val, path)
                    for val, path in zip(moving_values, paths_a2m)
                ],
                lag_ratio=0.05,
                run_time=2.0,
            )
        )

        self.wait(0.4)

        # 3) MITM's public-values scratchpad (minimal)
        p_pub = MathTex(r"p = 7", font_size=34)
        alpha_pub = MathTex(r"\alpha = 3", font_size=34)
        A_pub = MathTex(r"A = 2", font_size=34)

        B_pub = MathTex(r"B = 5", font_size=34)
        B_pub.set_opacity(0)
        B_pub.set_stroke(opacity=0)

        self.render_scratchpad(
            actor_name="mitm",
            title_text="Public values",
            items=[p_pub, alpha_pub, A_pub, B_pub],
            buff=0.2,
        )

        self.wait(0.5)

        # 4) Forward p, α, A to Bob (to match earlier scenes)
        mitm_values = [p_move, alpha_move, A_move]

        self.play(
            LaggedStart(
                *[
                    MoveAlongPath(val, path)
                    for val, path in zip(mitm_values, paths_m2b)
                ],
                lag_ratio=0.05,
                run_time=2.0,
            )
        )

        self.wait(1.0)

        # 5) Bob responds with B (omitted scratchpad for brevity), MITM receives it
        self.play(
            FadeOut(p_move),
            FadeOut(alpha_move),
            FadeOut(A_move),
            run_time=0.5,
        )
        self.wait(0.2)

        B_move = MathTex(r"B = 5", font_size=34)

        bob_to_mitm_path = self.bob_to_mitm_path

        self.spawn_payload_at(
            B_move,
            bob_to_mitm_path.get_start(),
            run_time=0.4,
        )

        self.play(MoveAlongPath(B_move, bob_to_mitm_path), run_time=2.0)
        self.wait(0.4)

        self.play(
            B_pub.animate.set_opacity(1).set_stroke(opacity=1),
            run_time=0.6,
        )
        self.wait(0.4)

        mitm_to_alice_path = self.mitm_to_alice_path

        self.play(MoveAlongPath(B_move, mitm_to_alice_path), run_time=2.0)
        self.wait(0.4)

        self.play(FadeOut(B_move), run_time=0.4)

        self.wait(1.0)

        # 6) MITM brute-forces x from small p and α
        base_y = -1

        line1 = MathTex(
            r"x = 1 \;\;\Rightarrow\;\; \alpha^1 = 3 \equiv 3 \pmod{7}", font_size=30
        ).move_to([0, base_y, 0])

        self.play(Write(line1), run_time=1.5)
        self.wait(0.3)

        cross1 = MathTex(r"\times", color=RED, font_size=34)
        cross1.next_to(line1, RIGHT, buff=0.4)

        self.play(FadeIn(cross1), run_time=0.5)
        self.wait(0.6)

        line2 = MathTex(
            r"x = 2 \;\;\Rightarrow\;\; \alpha^2 = 9 \equiv 2 \pmod{7}", font_size=30
        ).move_to([0, base_y - 0.5, 0])

        self.play(Write(line2), run_time=1.5)
        self.wait(0.3)

        tick2 = MathTex(r"\checkmark", color=GREEN, font_size=34)
        tick2.next_to(line2, RIGHT, buff=0.4)

        self.play(FadeIn(tick2), run_time=0.5)
        self.wait(0.8)

        x_line = MathTex(r"x = 2", font_size=30).move_to([0, base_y - 1, 0])

        self.play(Write(x_line), run_time=1.0)
        self.wait(1.0)

        final_line = MathTex(r"K = 5^2 \equiv 4\pmod{7} ", font_size=30).move_to(
            [0, base_y - 1.5, 0]
        )

        self.play(Write(final_line), run_time=1.0)
        self.wait(1.0)


class DH5(NetworkScene):
    def construct(self):
        """
        Show a full MITM key-substitution attack where the attacker learns both K_A and K_B.
        """
        self.setup_layout(
            show_alice=True,
            show_mitm=True,
            show_bob=True,
            show_ca=False,
            show_ab_links=True,
            show_ca_links=False,
        )

        self.wait(0.3)

        # 1) Build bottom paths for DH messages
        self.build_ab_paths(offset_down=1.5)

        base_a2m = self.alice_to_mitm_path
        base_m2a = self.mitm_to_alice_path
        base_m2b = self.mitm_to_bob_path
        base_b2m = self.bob_to_mitm_path

        vertical_offsets = [UP * 0.4, ORIGIN, DOWN * 0.4]

        # 2) p, α, A appear under Alice → MITM
        p_move = MathTex(r"p", font_size=34)
        alpha_move = MathTex(r"\alpha", font_size=34)
        A_move = MathTex(r"A", font_size=34)

        moving_values = [p_move, alpha_move, A_move]

        paths_a2m = []
        paths_m2b = []

        for offset in vertical_offsets:
            paths_a2m.append(base_a2m.copy().shift(offset))
            paths_m2b.append(base_m2b.copy().shift(offset))

        for val, path in zip(moving_values, paths_a2m):
            self.spawn_payload_at(val, path.get_start(), run_time=0.4)

        self.wait(0.2)

        self.play(
            LaggedStart(
                *[
                    MoveAlongPath(val, path)
                    for val, path in zip(moving_values, paths_a2m)
                ],
                lag_ratio=0.05,
                run_time=2.0,
            )
        )

        self.play(*[FadeOut(value) for value in moving_values], run_time=0.4)

        self.wait(0.5)

        # 3) MITM stores K_A and reserves a slot for K_B
        K_B_mitm = MathTex(r"K_B", font_size=34)
        K_B_mitm.set_opacity(0)
        K_B_mitm.set_stroke(opacity=0)

        K_A_mitm = MathTex(r"K_A", font_size=34)

        self.render_scratchpad(
            actor_name="mitm",
            title_text="Keys;",
            items=[K_A_mitm, K_B_mitm],
            buff=0.2,
        )

        self.wait(0.5)

        # 4) MITM sends forged B to Alice
        B_to_alice = MathTex(r"B", font_size=34)

        self.spawn_payload_at(
            B_to_alice,
            base_m2a.get_start(),
            run_time=0.4,
        )

        self.play(MoveAlongPath(B_to_alice, base_m2a), run_time=2.0)
        self.wait(0.4)

        self.play(FadeOut(B_to_alice), run_time=0.4)
        self.wait(0.3)

        # 5) Alice stores K_A in her own scratchpad
        K_A_alice = MathTex(r"K_A", font_size=34)

        self.render_scratchpad(
            actor_name="alice",
            title_text="Keys;",
            items=[K_A_alice],
            buff=0.2,
        )

        self.wait(0.7)

        # 6) MITM forwards p, α, A on to Bob
        mitm_values = [p_move, alpha_move, A_move]

        self.play(
            LaggedStart(
                *[
                    MoveAlongPath(val, path)
                    for val, path in zip(mitm_values, paths_m2b)
                ],
                lag_ratio=0.05,
                run_time=2.0,
            )
        )

        self.play(*[FadeOut(value) for value in moving_values], run_time=0.4)

        self.wait(0.5)

        # 7) Bob computes K_B and stores it
        K_B_bob = MathTex(r"K_B", font_size=34)

        self.render_scratchpad(
            actor_name="bob",
            title_text="Keys;",
            items=[K_B_bob],
            buff=0.2,
        )

        self.wait(0.7)

        # 8) Bob sends B back to MITM, MITM reveals K_B
        B_to_mitm = MathTex(r"B", font_size=34)

        self.spawn_payload_at(
            B_to_mitm,
            base_b2m.get_start(),
            run_time=0.4,
        )

        self.play(MoveAlongPath(B_to_mitm, base_b2m), run_time=2.0)
        self.wait(0.4)

        self.play(
            K_B_mitm.animate.set_opacity(1).set_stroke(opacity=1),
            run_time=0.6,
        )
        self.wait(0.3)

        self.play(FadeOut(B_to_mitm), run_time=0.4)

        self.wait(1.0)


class DH6(NetworkScene):
    def construct(self):
        """
        Show how hashing protects against MITM tampering: equal hashes tick, mismatched hashes cross.
        """
        self.camera.frame.shift(UP * 0.2)

        self.setup_layout(
            show_alice=True,
            show_mitm=True,
            show_bob=True,
            show_ca=False,
            show_ab_links=True,
            show_ca_links=False,
        )

        self.wait(0.3)

        # 1) Build bottom paths
        self.build_ab_paths(offset_down=1.5)

        base_a2m = self.alice_to_mitm_path
        base_m2b = self.mitm_to_bob_path
        base_b2m = self.bob_to_mitm_path

        vertical_offsets = [UP * 0.4, DOWN * 0.8]

        # 2) Bob knows PU_A in his key vault
        self.wait(0.5)

        PU_A = MathTex(r"PU_A", font_size=28)

        self.render_scratchpad(
            actor_name="bob",
            title_text="Keyvault:",
            items=[PU_A],
            buff=0.4,
        )

        self.wait(0.5)

        # 3) Alice sends (p, α, A) twice, one copy to be hashed
        public_vals = MathTex(r"(p = 7, \alpha = 3, A = 2)", font_size=32)
        repeat_vals = MathTex(r"(p = 7, \alpha = 3, A = 2)", font_size=32)

        moving_values = [public_vals, repeat_vals]

        paths_a2m = []
        paths_m2b = []
        paths_b2m = []

        for offset in vertical_offsets:
            paths_a2m.append(base_a2m.copy().shift(offset))
            paths_m2b.append(base_m2b.copy().shift(offset))
            paths_b2m.append(base_b2m.copy().shift(offset))

        for val, path in zip(moving_values, paths_a2m):
            self.spawn_payload_at(val, path.get_start(), run_time=1)

        hash_val = MathTex(r"\texttt{ba7816bf8e\dots}", font_size=34).move_to(
            repeat_vals
        )

        self.play(Transform(repeat_vals, hash_val), run_time=0.6)

        outer_rect = SurroundingRectangle(repeat_vals, buff=0.3, color=GREEN)
        self.play(Create(outer_rect), run_time=0.6)

        moving_values[1] = VGroup(repeat_vals, outer_rect)

        self.wait(0.2)

        # Alice → MITM
        self.play(
            LaggedStart(
                *[
                    MoveAlongPath(val, path)
                    for val, path in zip(moving_values, paths_a2m)
                ],
                lag_ratio=0.05,
                run_time=2.0,
            )
        )

        self.wait(0.4)

        # MITM → Bob, first (untampered) round
        self.play(
            LaggedStart(
                *[
                    MoveAlongPath(val, path)
                    for val, path in zip(moving_values, paths_m2b)
                ],
                lag_ratio=0.05,
                run_time=2.0,
            )
        )

        self.wait(1.0)

        self.play(Uncreate(outer_rect), run_time=0.6)

        new_hash_val = MathTex(r"\texttt{ba7816bf8e\dots}", font_size=34).move_to(
            public_vals
        )

        self.play(Transform(public_vals, new_hash_val), run_time=0.6)

        tick2 = MathTex(r"\checkmark", color=GREEN, font_size=40)
        tick2.next_to(repeat_vals, RIGHT, buff=0.4)

        self.play(FadeIn(tick2), run_time=0.5)
        self.wait(0.8)

        # Reverse messages to MITM so we can show a second, tampered attempt
        self.play(FadeOut(tick2), run_time=0.1)
        self.play(
            Transform(
                public_vals,
                MathTex(r"(p = 7, \alpha = 3, A = 2)", font_size=32).move_to(
                    public_vals
                ),
            ),
            run_time=0.1,
        )

        outer_rect = SurroundingRectangle(repeat_vals, buff=0.3, color=GREEN)
        self.play(Create(outer_rect), run_time=0.6)

        moving_values[1] = VGroup(repeat_vals, outer_rect)

        self.play(
            *[MoveAlongPath(val, path) for val, path in zip(moving_values, paths_b2m)],
            run_time=0.2,
        )

        # Now MITM tampers with the values
        mitm_vals = MathTex(
            r"(p = 101, \alpha = 3, A = 2)", font_size=32, color=RED
        ).move_to(public_vals)

        self.wait(1)

        self.play(TransformMatchingTex(public_vals, mitm_vals), run_time=1)

        self.wait(0.5)

        self.play(Uncreate(outer_rect), run_time=0.6)

        self.wait(0.5)

        outer_rect = SurroundingRectangle(repeat_vals, buff=0.3, color=RED)
        self.play(Create(outer_rect), run_time=0.6)

        moving_values[0] = mitm_vals
        final_box = VGroup(repeat_vals, outer_rect)
        moving_values[1] = final_box

        # MITM → Bob again with tampered values
        self.play(
            LaggedStart(
                *[
                    MoveAlongPath(val, path)
                    for val, path in zip(moving_values, paths_m2b)
                ],
                lag_ratio=0.05,
                run_time=2.0,
            )
        )

        self.wait(1.0)

        self.play(Uncreate(outer_rect), run_time=0.6)

        corrupted_hash = MathTex(r"\texttt{9a2b367fa\dots}", font_size=34).move_to(
            repeat_vals
        )

        self.play(Transform(repeat_vals, corrupted_hash), run_time=0.6)

        new_hash_val = MathTex(
            r"\texttt{2eeb178ab5\dots}", font_size=34, color=RED
        ).move_to(mitm_vals)

        self.play(Transform(mitm_vals, new_hash_val), run_time=0.6)

        cross = MathTex(r"\times", color=RED, font_size=40)
        cross.next_to(repeat_vals, RIGHT, buff=0.4)

        self.play(FadeIn(cross), run_time=0.5)
        self.wait(0.8)


class DH8(NetworkScene):
    def construct(self):
        """
        Introduce a certificate authority and show how signed certificates authenticate DH public values.
        """
        self.camera.frame.shift(UP * 1)

        self.setup_layout(
            show_alice=True,
            show_mitm=True,
            show_bob=True,
            show_ca=True,
            show_ab_links=True,
            show_ca_links=True,
            animate_actors=["ca"],
            animate_links=["alice_ca", "bob_ca"],
        )

        self.wait(0.3)

        self.animate_entrance(run_time=0.8)
        self.wait(0.3)

        # 1) Alice's key scratchpad with public/private key and placeholder for K
        PU_A = MathTex(r"PU_A", font_size=30)
        PR_A = MathTex(r"PR_A", font_size=30)

        Ka_sp = MathTex(r"K", font_size=30)
        Ka_sp.set_opacity(0)
        Ka_sp.set_stroke(opacity=0)

        self.render_scratchpad(
            actor_name="alice",
            title_text="Keys;",
            items=[PU_A, PR_A, Ka_sp],
            buff=0.4,
            left_shift=2,
            down_shift=2,
        )

        self.wait(0.6)

        # 2) Build Alice ↔ CA paths and stack two lanes
        self.build_ca_paths()
        base_a2ca = self.alice_to_ca_path

        vertical_offsets = [UP * 1.2 + LEFT * 0.4, UP * 0.3 + LEFT * 0.4]

        paths_a2ca = [base_a2ca.copy().shift(offset) for offset in vertical_offsets]

        # 3) Plain (PU_A, Alice) and a second copy that will become the signature
        plain_payload = MathTex(
            r"(PU_A, \text{Alice})",
            font_size=32,
        )

        signed_payload = MathTex(
            r"(PU_A, \text{Alice})",
            font_size=32,
        )

        moving_values = [plain_payload, signed_payload]

        for val, path in zip(moving_values, paths_a2ca):
            self.spawn_payload_at(val, path.get_start(), run_time=0.6)

        self.wait(0.4)

        # 4) Lower copy becomes a hash-like signature, boxed in green
        hex_signature = MathTex(
            r"\texttt{ba7816bf8e\dots}",
            font_size=32,
        ).move_to(signed_payload)

        self.play(Transform(signed_payload, hex_signature), run_time=0.6)

        sig_box = SurroundingRectangle(
            signed_payload,
            buff=0.3,
            color=GREEN,
        )
        self.play(Create(sig_box), run_time=0.6)

        signed_group = VGroup(signed_payload, sig_box)
        moving_values[1] = signed_group

        self.wait(0.4)

        # 5) Send both plaintext and signed copy to the CA
        self.play(
            LaggedStart(
                *[
                    MoveAlongPath(
                        val,
                        path,
                    )
                    for val, path in zip(moving_values, paths_a2ca)
                ],
                lag_ratio=0.05,
                run_time=2.0,
            )
        )

        self.wait(1.0)

        # 6) CA verifies Alice's signature
        self.play(FadeOut(sig_box), run_time=0.4)
        self.wait(0.2)

        ca_hash = MathTex(
            r"\texttt{ba7816bf8e\dots}",
            font_size=32,
        ).move_to(plain_payload)

        self.play(Transform(plain_payload, ca_hash), run_time=0.6)
        self.wait(0.2)

        ca_tick = MathTex(r"\checkmark", color=GREEN, font_size=40)
        ca_tick.next_to(plain_payload, RIGHT, buff=0.4)

        self.play(FadeIn(ca_tick), run_time=0.5)
        self.wait(0.6)

        self.play(
            FadeOut(plain_payload),
            FadeOut(signed_payload),
            FadeOut(ca_tick),
            run_time=0.6,
        )
        self.wait(0.4)

        # 7) CA creates Alice's certificate and sends it back
        base_ca2a = self.ca_to_alice_path
        cert_paths_ca2a = [
            base_ca2a.copy().shift(offset) for offset in vertical_offsets
        ]

        cert_plain = MathTex(
            r"(PU_A, \text{Alice}, \text{Demo CA})",
            font_size=32,
        )

        cert_plain_copy = MathTex(
            r"(PU_A, \text{Alice}, \text{Demo CA})",
            font_size=32,
        )

        cert_values = [cert_plain, cert_plain_copy]

        for val, path in zip(cert_values, cert_paths_ca2a):
            self.spawn_payload_at(val, path.get_start(), run_time=0.6)

        self.wait(0.4)

        cert_sig_text = MathTex(
            r"\texttt{9af13c42b\dots}",
            font_size=32,
        ).move_to(cert_plain_copy)

        self.play(Transform(cert_plain_copy, cert_sig_text), run_time=0.6)

        cert_sig_box = SurroundingRectangle(
            cert_plain_copy,
            buff=0.3,
            color=YELLOW,
        )
        self.play(Create(cert_sig_box), run_time=0.6)

        cert_sig_group = VGroup(cert_plain_copy, cert_sig_box)
        cert_values[1] = cert_sig_group

        self.play(
            LaggedStart(
                *[
                    MoveAlongPath(val, path)
                    for val, path in zip(cert_values, cert_paths_ca2a)
                ],
                lag_ratio=-0.05,
                run_time=2.0,
            )
        )

        self.wait(1.0)

        self.play(FadeOut(*[elem for elem in cert_values]), run_time=1)

        # 8) Alice sends DH values, signed hash, and CERT_A via MITM to Bob
        self.build_ab_paths(offset_down=1.5)

        base_a2m = self.alice_to_mitm_path
        base_m2b = self.mitm_to_bob_path

        triple_offsets = [UP * 0.5, DOWN * 0.15, DOWN * 0.8]

        paths_a2m_triple = [base_a2m.copy().shift(off) for off in triple_offsets]
        paths_m2b_triple = [base_m2b.copy().shift(off) for off in triple_offsets]

        dh_plain = MathTex(
            r"(p = 7, \alpha = 3, A = 2)",
            font_size=30,
        )

        dh_signed = MathTex(
            r"(p = 7, \alpha = 3, A = 2)",
            font_size=30,
        )

        cert_A = MathTex(
            r"CERT_A",
            font_size=30,
        )

        triple_values = [dh_plain, dh_signed, cert_A]

        for val, path in zip(triple_values, paths_a2m_triple):
            self.spawn_payload_at(val, path.get_start(), run_time=0.6)

        self.wait(0.4)

        dh_hex = MathTex(
            r"\texttt{ba7816bf8e\dots}",
            font_size=32,
        ).move_to(dh_signed)

        self.play(Transform(dh_signed, dh_hex), run_time=0.6)

        sig_box2 = SurroundingRectangle(
            dh_signed,
            buff=0.3,
            color=GREEN,
        )
        self.play(Create(sig_box2), run_time=0.6)

        signed_group2 = VGroup(dh_signed, sig_box2)
        triple_values[1] = signed_group2

        self.wait(0.4)

        self.play(
            LaggedStart(
                *[
                    MoveAlongPath(val, path)
                    for val, path in zip(triple_values, paths_a2m_triple)
                ],
                lag_ratio=0.05,
                run_time=2.0,
            )
        )

        self.wait(0.4)

        self.play(
            LaggedStart(
                *[
                    MoveAlongPath(val, path)
                    for val, path in zip(triple_values, paths_m2b_triple)
                ],
                lag_ratio=0.05,
                run_time=2.0,
            )
        )

        self.wait(1.0)

        # 9) Bob verifies CERT_A and the DH signature
        cert_tick = MathTex(r"\checkmark", color=GREEN, font_size=36)
        cert_tick.next_to(cert_A, RIGHT, buff=0.2)

        self.play(FadeIn(cert_tick), run_time=0.4)
        self.wait(0.3)

        self.play(FadeOut(sig_box2), run_time=0.4)
        self.wait(0.2)

        bob_hash = MathTex(
            r"\texttt{ba7816bf8e\dots}",
            font_size=32,
        ).move_to(dh_plain)

        self.play(Transform(dh_plain, bob_hash), run_time=0.6)
        self.wait(0.2)

        sig_tick = MathTex(r"\checkmark", color=GREEN, font_size=36)
        sig_tick.next_to(dh_plain, RIGHT, buff=0.2)

        self.play(FadeIn(sig_tick), run_time=0.4)
        self.wait(0.8)

        self.play(
            FadeOut(dh_plain),
            FadeOut(dh_signed),
            FadeOut(cert_A),
            FadeOut(cert_tick),
            FadeOut(sig_tick),
            run_time=0.6,
        )
        self.wait(0.4)

        # 10) Bob's key scratchpad with PU_B, PR_B, K
        PU_B = MathTex(r"PU_B", font_size=30)
        PR_B = MathTex(r"PR_B", font_size=30)
        K_B = MathTex(r"K", font_size=30)

        self.render_scratchpad(
            actor_name="bob",
            title_text="Keys;",
            items=[PU_B, PR_B, K_B],
            buff=0.4,
            left_shift=-2,
            down_shift=2,
        )

        self.wait(0.6)

        # 11) Bob sends (PU_B, Bob) and signature to CA
        self.build_ca_paths()

        base_b2ca = self.bob_to_ca_path

        vertical_offsets_bob = [UP * 3 + RIGHT * 1.2, UP * 2.1 + RIGHT * 1.2]
        paths_b2ca = [base_b2ca.copy().shift(off) for off in vertical_offsets_bob]

        plain_payload_B = MathTex(
            r"(PU_B, \text{Bob})",
            font_size=32,
        )

        signed_payload_B = MathTex(
            r"(PU_B, \text{Bob})",
            font_size=32,
        )

        moving_values_B = [plain_payload_B, signed_payload_B]

        for val, path in zip(moving_values_B, paths_b2ca):
            self.spawn_payload_at(val, path.get_start(), run_time=0.6)

        self.wait(0.4)

        hex_signature_B = MathTex(
            r"\texttt{c4d29af7e\dots}",
            font_size=32,
        ).move_to(signed_payload_B)

        self.play(Transform(signed_payload_B, hex_signature_B), run_time=0.6)

        sig_box_B = SurroundingRectangle(
            signed_payload_B,
            buff=0.3,
            color=BLUE,
        )
        self.play(Create(sig_box_B), run_time=0.6)

        signed_group_B = VGroup(signed_payload_B, sig_box_B)
        moving_values_B[1] = signed_group_B

        self.wait(0.4)

        self.play(
            LaggedStart(
                *[
                    MoveAlongPath(val, path)
                    for val, path in zip(moving_values_B, paths_b2ca)
                ],
                lag_ratio=0.05,
                run_time=2.0,
            )
        )

        self.wait(1.0)

        # 12) CA verifies Bob's signature
        self.play(FadeOut(sig_box_B), run_time=0.4)
        self.wait(0.2)

        ca_hash_B = MathTex(
            r"\texttt{c4d29af7e\dots}",
            font_size=32,
        ).move_to(plain_payload_B)

        self.play(Transform(plain_payload_B, ca_hash_B), run_time=0.6)
        self.wait(0.2)

        ca_tick_B = MathTex(r"\checkmark", color=GREEN, font_size=40)
        ca_tick_B.next_to(plain_payload_B, RIGHT, buff=0.4)

        self.play(FadeIn(ca_tick_B), run_time=0.5)
        self.wait(0.6)

        self.play(
            FadeOut(plain_payload_B),
            FadeOut(signed_payload_B),
            FadeOut(ca_tick_B),
            run_time=0.6,
        )
        self.wait(0.4)

        # 13) CA creates Bob's certificate and sends it to Bob
        base_ca2b = self.ca_to_bob_path
        cert_paths_ca2b = [base_ca2b.copy().shift(off) for off in vertical_offsets_bob]

        cert_plain_B = MathTex(
            r"(PU_B, \text{Bob}, \text{Demo CA})",
            font_size=32,
        )
        cert_plain_B_copy = MathTex(
            r"(PU_B, \text{Bob}, \text{Demo CA})",
            font_size=32,
        )

        cert_values_B = [cert_plain_B, cert_plain_B_copy]

        for val, path in zip(cert_values_B, cert_paths_ca2b):
            self.spawn_payload_at(val, path.get_start(), run_time=0.6)

        self.wait(0.4)

        cert_sig_text_B = MathTex(
            r"\texttt{8b91fa7c3\dots}",
            font_size=32,
        ).move_to(cert_plain_B_copy)

        self.play(Transform(cert_plain_B_copy, cert_sig_text_B), run_time=0.6)

        cert_sig_box_B = SurroundingRectangle(
            cert_plain_B_copy,
            buff=0.3,
            color=YELLOW,
        )
        self.play(Create(cert_sig_box_B), run_time=0.6)

        cert_sig_group_B = VGroup(cert_plain_B_copy, cert_sig_box_B)
        cert_values_B[1] = cert_sig_group_B

        self.play(
            LaggedStart(
                *[
                    MoveAlongPath(val, path)
                    for val, path in zip(cert_values_B, cert_paths_ca2b)
                ],
                lag_ratio=-0.05,
                run_time=2.0,
            )
        )

        self.wait(1.0)

        self.play(FadeOut(*[elem for elem in cert_values_B]), run_time=1.0)
        self.wait(0.4)

        # 14) Bob sends (p, α, B), signed copy, and CERT_B via MITM to Alice
        self.build_ab_paths(offset_down=1.5)

        base_b2m = self.bob_to_mitm_path
        base_m2a = self.mitm_to_alice_path

        triple_offsets_B = [UP * 0.5, DOWN * 0.15, DOWN * 0.8]

        paths_b2m_triple = [base_b2m.copy().shift(off) for off in triple_offsets_B]
        paths_m2a_triple = [base_m2a.copy().shift(off) for off in triple_offsets_B]

        dh_plain_B = MathTex(
            r"(p = 7, \alpha = 3, B = 5)",
            font_size=30,
        )

        dh_signed_B = MathTex(
            r"(p = 7, \alpha = 3, B = 5)",
            font_size=30,
        )

        cert_B = MathTex(
            r"CERT_B",
            font_size=30,
        )

        triple_values_B = [dh_plain_B, dh_signed_B, cert_B]

        for val, path in zip(triple_values_B, paths_b2m_triple):
            self.spawn_payload_at(val, path.get_start(), run_time=0.6)

        self.wait(0.4)

        dh_hex_B = MathTex(
            r"\texttt{c4d29af7e\dots}",
            font_size=32,
        ).move_to(dh_signed_B)

        self.play(Transform(dh_signed_B, dh_hex_B), run_time=0.6)

        sig_box_B2 = SurroundingRectangle(
            dh_signed_B,
            buff=0.3,
            color=BLUE,
        )
        self.play(Create(sig_box_B2), run_time=0.6)

        signed_group_B2 = VGroup(dh_signed_B, sig_box_B2)
        triple_values_B[1] = signed_group_B2

        self.wait(0.4)

        # Bob → MITM
        self.play(
            LaggedStart(
                *[
                    MoveAlongPath(val, path)
                    for val, path in zip(triple_values_B, paths_b2m_triple)
                ],
                lag_ratio=0.05,
                run_time=2.0,
            )
        )

        self.wait(0.4)

        # MITM → Alice
        self.play(
            LaggedStart(
                *[
                    MoveAlongPath(val, path)
                    for val, path in zip(triple_values_B, paths_m2a_triple)
                ],
                lag_ratio=0.05,
                run_time=2.0,
            )
        )

        self.wait(1.0)

        self.play(
            Ka_sp.animate.set_opacity(1).set_stroke(opacity=1),
            run_time=0.6,
        )

        self.play(FadeOut(*[elem for elem in triple_values_B]))
