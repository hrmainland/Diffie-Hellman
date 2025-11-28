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
        animate_actors=None,  # NEW: which actors should appear via animation
        animate_links=None,  # NEW: which links should appear via animation
    ):
        # normalise config
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

        # For later
        self.actors_to_animate = []
        self.links_to_animate = []

        # ---------- create actors ----------
        if show_alice:
            self.actors["alice"] = self._make_actor("Alice", self.actor_points["alice"])
        if show_mitm:
            self.actors["mitm"] = self._make_actor("MITM", self.actor_points["mitm"])
        if show_bob:
            self.actors["bob"] = self._make_actor("Bob", self.actor_points["bob"])
        if show_ca:
            self.actors["ca"] = self._make_actor("CA", self.actor_points["ca"])

        # decide which actors are static vs animated
        actors_to_add = []
        for name, actor in self.actors.items():
            if name in animate_actors:
                self.actors_to_animate.append(actor)
            else:
                actors_to_add.append(actor)

        # ---------- create links ----------
        if show_ab_links:
            # Alice <-> MITM
            if "alice" in self.actors and "mitm" in self.actors:
                self.links["alice_mitm"] = self._make_link("alice", "mitm")

            # MITM <-> Bob
            if "mitm" in self.actors and "bob" in self.actors:
                self.links["mitm_bob"] = self._make_link("mitm", "bob")

            # Direct Alice <-> Bob ONLY when there is no MITM
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

        # decide which links are static vs animated
        links_to_add = []
        for name, link in self.links.items():
            if name in animate_links:
                self.links_to_animate.append(link)
            else:
                links_to_add.append(link)

        # ---------- add statically-present stuff to the scene ----------
        self.add(*actors_to_add, *links_to_add)

    def animate_entrance(self, run_time=0.8):
        """
        Animate in all actors and links that were marked for animation in setup_layout.
        - actors: FadeIn
        - links: Create
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
        box_a = self.actor_boxes[actor_a]
        box_b = self.actor_boxes[actor_b]

        # bottom horizontal line (Alice/MITM/Bob)
        if {actor_a, actor_b} <= {"alice", "mitm", "bob"}:
            if box_a.get_center()[0] < box_b.get_center()[0]:
                start = box_a.get_right()
                end = box_b.get_left()
            else:
                start = box_b.get_right()
                end = box_a.get_left()
            return Line(start, end)

        # slanted lines to CA
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

        # fallback generic line
        direction = box_b.get_center() - box_a.get_center()
        direction = direction / np.linalg.norm(direction)
        start = box_a.get_boundary_point(direction)
        end = box_b.get_boundary_point(-direction)
        return Line(start, end)

    # ---------- packet path helpers (for CA) ----------

    def _offset_path(self, base_start, base_end, offset=1.0, shorten_factor=0.2):
        v = base_end - base_start
        length = np.linalg.norm(v)
        direction = v / length

        perp = np.array([-direction[1], direction[0], 0.0])
        perp = perp / np.linalg.norm(perp)

        start = base_start + perp * offset
        end = base_end + perp * offset - direction * (length * shorten_factor)
        return Line(start, end)

    def build_ca_paths(self):
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

    # ---------- NEW: bottom-line Alice/MITM/Bob path helpers ----------

    def _downshift_line(self, line, offset=1.5):
        """Return a copy of `line` shifted straight down by `offset`."""
        return Line(
            line.get_start() + DOWN * offset,
            line.get_end() + DOWN * offset,
        )

    # ---------- bottom-line Alice/MITM/Bob path helpers ----------

    def build_ab_paths(self, offset_down=1.5):
        """
        Define offset paths for:
        - Alice ↔ MITM
        - MITM ↔ Bob
        - Alice ↔ Bob (direct)
        All start/end directly under the actors (bottom center), shifted down.
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
        Default way to put any non-actor, non-link Mobject onto the screen
        with a nice entrance animation.

        - `payload` is any Mobject (packet, circle, Tex, VGroup, etc.)
        - `point` is where it should appear (often path.get_start()).
        """
        payload.move_to(point)

        if isinstance(payload, MathTex) or isinstance(payload, Text):
            self.play(Write(payload), run_time=run_time)
            return payload

        if entrance_anim is None:
            # Default entrance: slight grow + fade
            entrance_anim = FadeIn(payload, scale=0.8, shift=UP * 0.1)

        self.play(entrance_anim, run_time=run_time)
        return payload

    def move_payload_along_path(self, payload, path, run_time=2, pause_after=0):
        """
        Move an already-spawned payload along a path.
        Assumes the payload is already visible from spawn_payload_at.
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
        Render a 'scratchpad card' above a given actor.

        - actor_name: "alice", "bob", "mitm", "ca"
        - title_text: string for the card title (uses Text)
        - items: iterable of pre-built Mobjects (MathTex, Text, etc.)
        - buff: vertical spacing between actor box and scratchpad
        """

        actor_box = self.actor_boxes[actor_name]

        # Title
        title = Text(title_text, font_size=28)

        # Column of provided items (MathTex/Text), left-aligned
        column = VGroup(*items).arrange(DOWN, aligned_edge=LEFT, buff=0.15)

        # Title above column
        content = VGroup(title, column).arrange(DOWN, buff=0.25, aligned_edge=LEFT)

        # Surrounding card
        panel = SurroundingRectangle(
            content,
            buff=0.3,
            color=panel_color,
            corner_radius=0.15,
            stroke_width=2,
        )

        card = VGroup(panel, content)

        # Position the card above the actor:
        # 1) vertically 'above' with a buffer
        card.next_to(actor_box, UP, buff=buff)
        # 2) horizontally centre the card over the actor
        card.move_to(np.array([actor_box.get_center()[0], card.get_center()[1], 0.0]))
        card.shift(LEFT * left_shift)
        card.shift(DOWN * down_shift)

        # --- Animate card + entries in ---

        # Panel first
        self.play(FadeIn(panel, shift=UP * 0.1, scale=0.95), run_time=0.4)

        # Then title
        self.play(Write(title), run_time=0.4)

        # Then each item (p, α, x, A, etc.)
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
        # Direct Alice ↔ Bob, no MITM, no CA
        self.setup_layout(
            show_alice=True,
            show_mitm=False,
            show_bob=True,
            show_ca=False,
            show_ab_links=True,  # creates alice_bob (because no MITM)
            show_ca_links=False,
            animate_actors=["alice", "bob"],  # animate people in
            animate_links=["alice_bob"],  # animate direct link in
        )

        # Animate Alice, Bob, and the direct link entering
        self.animate_entrance(run_time=0.8)

        # Build the bottom packet paths (includes alice_to_bob_path & bob_to_alice_path)
        self.build_ab_paths(offset_down=1.5)

        self.wait(3)

        # ------- Alice → Bob: "Morning Bob" -------

        # Plain string → Text (not MathTex)
        msg_to_bob = Text("Morning Bob", font_size=32)

        # Spawn under Alice with your default entrance animation
        self.spawn_payload_at(
            msg_to_bob,
            self.alice_to_bob_path.get_start(),
            run_time=0.6,
        )

        # Move message along Alice → Bob
        self.play(MoveAlongPath(msg_to_bob, self.alice_to_bob_path), run_time=2.0)
        self.wait(0.3)

        # Fade out the first message at Bob
        self.play(FadeOut(msg_to_bob), run_time=0.4)
        self.wait(0.2)

        # ------- Bob → Alice: "Hi Alice" -------

        msg_to_alice = Text("Hi Alice", font_size=32)

        # Spawn under Bob (start of the return path)
        self.spawn_payload_at(
            msg_to_alice,
            self.bob_to_alice_path.get_start(),
            run_time=0.6,
        )

        # Move message along Bob → Alice
        self.play(MoveAlongPath(msg_to_alice, self.bob_to_alice_path), run_time=2.0)

        self.wait(1.0)


class DH1(NetworkScene):
    def construct(self):
        # Alice and Bob are "already there" (no animation for them),
        # MITM + its links will animate in.
        self.setup_layout(
            show_alice=True,
            show_mitm=True,
            show_bob=True,
            show_ca=False,
            show_ab_links=True,  # alice_mitm + mitm_bob (no direct alice_bob when mitm present)
            show_ca_links=False,
            animate_actors=["mitm"],  # animate MITM appearing
            animate_links=["alice_mitm", "mitm_bob"],  # animate links to MITM
        )

        # Build bottom paths for Alice–MITM–Bob
        self.build_ab_paths(offset_down=1.5)

        self.wait(0.3)

        # Animate MITM + its links onto the screen
        self.animate_entrance(run_time=0.8)

        self.wait(27)

        # ---------- Alice → MITM → Bob: "What's your pin number again?" ----------

        msg_to_bob = Text("What's your pin?", font_size=30)

        # Spawn under Alice on the Alice→MITM path
        self.spawn_payload_at(
            msg_to_bob,
            self.alice_to_mitm_path.get_start(),
            run_time=0.6,
        )

        # Alice → MITM
        self.play(MoveAlongPath(msg_to_bob, self.alice_to_mitm_path), run_time=2.0)
        self.wait(0.4)  # pause at MITM

        # MITM → Bob (same object, no disappear/reappear)
        self.play(MoveAlongPath(msg_to_bob, self.mitm_to_bob_path), run_time=2.0)
        self.wait(0.3)

        # Optionally clear the first message once delivered to Bob
        self.play(FadeOut(msg_to_bob), run_time=0.4)
        self.wait(0.2)

        # ---------- Bob → MITM → Alice: "It's 4293" ----------

        reply = Text("It's 4293", font_size=30)

        # Spawn under Bob on the Bob→MITM path
        self.spawn_payload_at(
            reply,
            self.bob_to_mitm_path.get_start(),
            run_time=0.6,
        )

        # Bob → MITM
        self.play(MoveAlongPath(reply, self.bob_to_mitm_path), run_time=2.0)
        self.wait(0.4)  # pause at MITM

        # MITM → Alice
        self.play(MoveAlongPath(reply, self.mitm_to_alice_path), run_time=2.0)

        self.wait(1.0)


class DH2pre(NetworkScene):
    def construct(self):
        # Alice, MITM, Bob present (no CA)
        self.setup_layout(
            show_alice=True,
            show_mitm=True,
            show_bob=True,
            show_ca=False,
            show_ab_links=True,
            show_ca_links=False,
        )

        self.wait(0.3)

        # ------------------------------------------------------------
        # 1) Alice's scratchpad above her: p, α, x, A = α^x mod p
        # ------------------------------------------------------------

        p_sp = MathTex(r"p", font_size=30)
        alpha_sp = MathTex(r"\alpha", font_size=30)
        x_sp = MathTex(r"x", font_size=30)
        A_sp = MathTex(r"A = \alpha^x \bmod p", font_size=30)

        # Hidden placeholder for Bob's public value B (blank row for now)
        B_sp = MathTex(r"B = \alpha^y \bmod p", font_size=30)
        B_sp.set_opacity(0)
        B_sp.set_stroke(opacity=0)

        # Hidden placeholder for shared Key
        K_sp = MathTex(r"K = B^x \bmod p", font_size=30)
        K_sp.set_opacity(0)
        K_sp.set_stroke(opacity=0)

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
            ],  # B row reserved but invisible
            buff=0.2,
            delays=[2, 2.4, 6.2, 3.9],
        )

        self.wait(5)

        # ------------------------------------------------------------
        # 2) Build bottom paths: Alice ↔ MITM ↔ Bob
        # ------------------------------------------------------------

        self.build_ab_paths(offset_down=1.5)

        base_a2m = self.alice_to_mitm_path
        base_m2b = self.mitm_to_bob_path

        # We will stack three values vertically using shifted copies of the base paths
        vertical_offsets = [UP * 0.4, ORIGIN, DOWN * 0.4]

        # ------------------------------------------------------------
        # 3) p, α, x appear under Alice, stacked, then go to MITM
        # ------------------------------------------------------------

        # Moving versions (separate from scratchpad items)
        p_move = MathTex(r"p", font_size=34)
        alpha_move = MathTex(r"\alpha", font_size=34)
        A_move = MathTex(r"A = \alpha^x \bmod p", font_size=34)

        moving_values = [p_move, alpha_move, A_move]

        # Build per-value paths Alice→MITM and MITM→Bob
        paths_a2m = []
        paths_m2b = []

        for offset in vertical_offsets:
            paths_a2m.append(base_a2m.copy().shift(offset))
            paths_m2b.append(base_m2b.copy().shift(offset))

        # Spawn p, α, x under Alice on their respective paths
        for val, path in zip(moving_values, paths_a2m):
            self.spawn_payload_at(val, path.get_start(), run_time=0.4)

        self.wait(0.2)

        # Alice → MITM with LaggedStart
        self.play(
            LaggedStart(
                *[
                    MoveAlongPath(val, path)
                    for val, path in zip(moving_values, paths_a2m)
                ],
                lag_ratio=0.05,  # 0.05 * 2s = 0.1s between starts if run_time=2
                run_time=2.0,
            )
        )

        # ------------------------------------------------------------
        # 4) At MITM, turn x into A and create "Public values" scratchpad
        # ------------------------------------------------------------

        p_pub = MathTex(r"p", font_size=34)
        alpha_pub = MathTex(r"\alpha", font_size=34)
        A_pub = MathTex(r"A = \alpha^x \bmod p", font_size=34)

        # Hidden placeholder for B in MITM's view of public values
        B_pub = MathTex(r"B = \alpha^y \bmod p", font_size=34)
        B_pub.set_opacity(0)
        B_pub.set_stroke(opacity=0)

        self.render_scratchpad(
            actor_name="mitm",
            title_text="Public values",
            items=[p_pub, alpha_pub, A_pub, B_pub],
            buff=0.2,
        )

        # ------------------------------------------------------------
        # 5) Move p, α, A (the three values under MITM) over to Bob
        # ------------------------------------------------------------

        # At this point, under MITM we have:
        # - p_move (p)
        # - alpha_move (α)
        # - A_move
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

        # ------------------------------------------------------------
        # 6) Bob's scratchpad with all his DH values
        # ------------------------------------------------------------

        # Bob's view:
        #  - p, α, A  (public / received)
        #  - B = α^y mod p (his own public value)
        #  - K = A^y mod p (shared key)
        #
        # (All fully visible from the start of this card.)

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

        # ------------------------------------------------------------
        # 7) Replace values under Bob with B, send B back to MITM
        # ------------------------------------------------------------

        # Remove the three values p, α, A that are under Bob
        self.play(
            FadeOut(p_move),
            FadeOut(alpha_move),
            FadeOut(A_move),
            run_time=0.5,
        )
        self.wait(0.5)

        # Create a single B message under Bob
        B_move = MathTex(r"B = \alpha^y \bmod p", font_size=34)

        # Use the central Bob → MITM bottom path
        bob_to_mitm_path = self.bob_to_mitm_path

        self.spawn_payload_at(
            B_move,
            bob_to_mitm_path.get_start(),
            run_time=0.4,
        )

        # Bob → MITM (B travelling)
        self.play(MoveAlongPath(B_move, bob_to_mitm_path), run_time=2.0)
        self.wait(0.4)

        # ------------------------------------------------------------
        # 8) Reveal B in MITM's scratchpad, then send B to Alice
        # ------------------------------------------------------------

        # Unhide B_pub in "Public values" scratchpad
        self.play(
            B_pub.animate.set_opacity(1).set_stroke(opacity=1),
            run_time=0.6,
        )
        self.wait(0.4)

        # Now send B from MITM to Alice
        mitm_to_alice_path = self.mitm_to_alice_path

        self.play(MoveAlongPath(B_move, mitm_to_alice_path), run_time=2.0)
        self.wait(0.4)

        # ------------------------------------------------------------
        # 9) Alice stores B and K in her scratchpad (unhide rows)
        # ------------------------------------------------------------

        # First reveal B row in Alice's scratchpad
        self.play(
            B_sp.animate.set_opacity(1).set_stroke(opacity=1),
            run_time=0.6,
        )
        self.wait(0.2)

        # Then reveal K row in Alice's scratchpad
        self.play(
            K_sp.animate.set_opacity(1).set_stroke(opacity=1),
            run_time=0.6,
        )
        self.wait(0.4)

        # (Optional) fade out the travelling B under Alice,
        # now that it is stored in her scratchpad
        self.play(FadeOut(B_move), run_time=0.4)

        self.wait(1.0)

        # ------------------------------------------------------------
        # 10) Duplicate K from Alice and Bob, slide + enlarge to bottom centre,
        #     then do algebra steps to show they are equal
        # ------------------------------------------------------------

        # Copies of K from Alice's and Bob's scratchpads
        K_alice_global = K_sp.copy()
        K_bob_global = K_bob.copy()

        # Start them exactly where the originals are
        K_alice_global.move_to(K_sp.get_center())
        K_bob_global.move_to(K_bob.get_center())

        # Put them on top of the originals
        self.add(K_alice_global, K_bob_global)

        # Decide where they should end up: stacked at bottom centre
        temp_group = VGroup(
            K_alice_global.copy(),
            K_bob_global.copy(),
        ).arrange(DOWN, buff=0.3)
        temp_group.move_to(DOWN * 1.8)  # around middle-bottom of the frame

        target_pos_alice = temp_group[0].get_center()
        target_pos_bob = temp_group[1].get_center()

        # Scale up from ~34 → 36 while sliding down
        scale_factor = 36 / 34

        self.play(
            K_alice_global.animate.move_to(target_pos_alice).scale(scale_factor),
            K_bob_global.animate.move_to(target_pos_bob).scale(scale_factor),
            run_time=1.5,
        )
        self.wait(0.5)

        # ------------------------------------------------------------
        # Algebra step 1: expand B and A inside K
        #   Top:    K = B^x mod p    → K = (α^y mod p)^x mod p
        #   Bottom: K = A^y mod p    → K = (α^x mod p)^y mod p
        # ------------------------------------------------------------

        k1_step1 = MathTex(
            r"K = (\alpha^y \bmod p)^x \bmod p",
            font_size=36,
        ).move_to(K_alice_global.get_center())

        k2_step1 = MathTex(
            r"K = (\alpha^x \bmod p)^y \bmod p",
            font_size=36,
        ).move_to(K_bob_global.get_center())

        # Top first
        self.play(Transform(K_alice_global, k1_step1), run_time=1.0)
        # Then bottom
        self.play(Transform(K_bob_global, k2_step1), run_time=1.0)
        self.wait(0.5)

        # ------------------------------------------------------------
        # Algebra step 2: remove inner "mod p" from inside the brackets
        #   (α^y mod p)^x mod p → (α^y)^x mod p
        #   (α^x mod p)^y mod p → (α^x)^y mod p
        # ------------------------------------------------------------

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

        # ------------------------------------------------------------
        # Algebra step 3: remove brackets and combine exponents
        #   (α^y)^x → α^{yx},  (α^x)^y → α^{xy}
        #   Show both as the same final expression: K = α^{xy} mod p
        # ------------------------------------------------------------

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

        # ------------------------------------------------------------
        # Final step: remove both K lines and show the "find x" equation
        # ------------------------------------------------------------

        # Compute a centre point between the two K lines
        final_center = (K_alice_global.get_center() + K_bob_global.get_center()) / 2

        # Fade out both K expressions
        self.play(
            FadeOut(K_alice_global),
            FadeOut(K_bob_global),
            run_time=0.6,
        )

        # Single discrete-log style line in their place
        dlp_line = MathTex(
            r"\text{Find } x \text{ such that } \alpha^x \equiv A \pmod p",
            font_size=36,
        )
        dlp_line.move_to(final_center)

        # Render that line and leave it on screen
        self.play(Write(dlp_line), run_time=1.2)
        self.wait(1.0)


class DH2(NetworkScene):
    def construct(self):

        self.camera.frame.shift(UP * 0.2)

        # Alice, MITM, Bob present (no CA)
        self.setup_layout(
            show_alice=True,
            show_mitm=True,
            show_bob=True,
            show_ca=False,
            show_ab_links=True,
            show_ca_links=False,
        )

        self.wait(0.3)

        # ------------------------------------------------------------
        # 1) Alice's scratchpad above her: p, α, x, A = α^x mod p
        # ------------------------------------------------------------

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

        # ------------------------------------------------------------
        # 2) Build bottom paths: Alice ↔ MITM ↔ Bob
        # ------------------------------------------------------------

        self.build_ab_paths(offset_down=1.5)

        base_a2m = self.alice_to_mitm_path
        base_m2b = self.mitm_to_bob_path

        # We will stack three values vertically using shifted copies of the base paths
        vertical_offsets = [UP * 0.4, ORIGIN, DOWN * 0.4]

        # ------------------------------------------------------------
        # 3) p, α, x appear under Alice, stacked, then go to MITM
        # ------------------------------------------------------------

        # Moving versions (separate from scratchpad items)
        p_move = MathTex(r"p = 7", font_size=34)
        alpha_move = MathTex(r"\alpha = 3", font_size=34)
        A_move = MathTex(r"A = 2", font_size=34)

        moving_values = [p_move, alpha_move, A_move]

        # Build per-value paths Alice→MITM and MITM→Bob
        paths_a2m = []
        paths_m2b = []

        for offset in vertical_offsets:
            paths_a2m.append(base_a2m.copy().shift(offset))
            paths_m2b.append(base_m2b.copy().shift(offset))

        # Spawn p, α, x under Alice on their respective paths
        for val, path in zip(moving_values, paths_a2m):
            self.spawn_payload_at(val, path.get_start(), run_time=0.4)

        self.wait(0.2)

        # Alice → MITM with LaggedStart
        self.play(
            LaggedStart(
                *[
                    MoveAlongPath(val, path)
                    for val, path in zip(moving_values, paths_a2m)
                ],
                lag_ratio=0.05,  # 0.05 * 2s = 0.1s between starts if run_time=2
                run_time=2.0,
            )
        )

        self.wait(0.4)  # pause under MITM

        # ------------------------------------------------------------
        # 4) At MITM, turn x into A and create "Public values" scratchpad
        # ------------------------------------------------------------

        p_pub = MathTex(r"p = 7", font_size=34)
        alpha_pub = MathTex(r"\alpha = 3", font_size=34)
        A_pub = MathTex(r"A = 2", font_size=34)

        # Hidden placeholder for B in MITM's view of public values
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

        # ------------------------------------------------------------
        # 5) Move p, α, A (the three values under MITM) over to Bob
        # ------------------------------------------------------------

        # At this point, under MITM we have:
        # - p_move (p)
        # - alpha_move (α)
        # - A_move
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

        # ------------------------------------------------------------
        # 6) Bob's scratchpad with all his DH values
        # ------------------------------------------------------------

        # Bob's view:
        #  - p, α, A  (public / received)
        #  - B = α^y mod p (his own public value)
        #  - K = A^y mod p (shared key)
        #
        # (All fully visible from the start of this card.)

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

        # ------------------------------------------------------------
        # 7) Replace values under Bob with B, send B back to MITM
        # ------------------------------------------------------------

        # Remove the three values p, α, A that are under Bob
        self.play(
            FadeOut(p_move),
            FadeOut(alpha_move),
            FadeOut(A_move),
            run_time=0.5,
        )
        self.wait(0.2)

        # Create a single B message under Bob
        B_move = MathTex(r"B = 5", font_size=34)

        # Use the central Bob → MITM bottom path
        bob_to_mitm_path = self.bob_to_mitm_path

        self.spawn_payload_at(
            B_move,
            bob_to_mitm_path.get_start(),
            run_time=0.4,
        )

        # Bob → MITM (B travelling)
        self.play(MoveAlongPath(B_move, bob_to_mitm_path), run_time=2.0)
        self.wait(0.4)

        # ------------------------------------------------------------
        # 8) Reveal B in MITM's scratchpad, then send B to Alice
        # ------------------------------------------------------------

        # Unhide B_pub in "Public values" scratchpad
        self.play(
            B_pub.animate.set_opacity(1).set_stroke(opacity=1),
            run_time=0.6,
        )
        self.wait(0.4)

        # Now send B from MITM to Alice
        mitm_to_alice_path = self.mitm_to_alice_path

        self.play(MoveAlongPath(B_move, mitm_to_alice_path), run_time=2.0)
        self.wait(0.4)

        # ------------------------------------------------------------
        # 9) Alice stores B and K in her scratchpad (unhide rows)
        # ------------------------------------------------------------

        # First reveal B row in Alice's scratchpad
        self.play(
            B_sp.animate.set_opacity(1).set_stroke(opacity=1),
            run_time=0.6,
        )
        self.wait(0.2)

        # Then reveal K row in Alice's scratchpad
        self.play(
            K_sp.animate.set_opacity(1).set_stroke(opacity=1),
            run_time=0.6,
        )
        self.wait(0.4)

        # (Optional) fade out the travelling B under Alice,
        # now that it is stored in her scratchpad
        self.play(FadeOut(B_move), run_time=0.4)

        self.wait(1.0)


class DH3(NetworkScene):
    def construct(self):

        self.camera.frame.shift(UP * 0.2)

        # Alice, MITM, Bob present (no CA)
        self.setup_layout(
            show_alice=True,
            show_mitm=True,
            show_bob=True,
            show_ca=False,
            show_ab_links=True,
            show_ca_links=False,
        )

        self.wait(0.3)

        # ------------------------------------------------------------
        # 1) Build bottom paths: Alice ↔ MITM ↔ Bob
        # ------------------------------------------------------------

        self.build_ab_paths(offset_down=1.5)

        base_a2m = self.alice_to_mitm_path
        base_m2b = self.mitm_to_bob_path

        # We will stack three values vertically using shifted copies of the base paths
        vertical_offsets = [UP * 0.4, ORIGIN, DOWN * 0.4]

        # ------------------------------------------------------------
        # 2) p, α, x appear under Alice, stacked, then go to MITM
        # ------------------------------------------------------------

        # Moving versions (separate from scratchpad items)
        p_move = MathTex(r"p = 7", font_size=34)
        alpha_move = MathTex(r"\alpha = 3", font_size=34)
        A_move = MathTex(r"A = 2", font_size=34)

        moving_values = [p_move, alpha_move, A_move]

        # Build per-value paths Alice→MITM and MITM→Bob
        paths_a2m = []
        paths_m2b = []

        for offset in vertical_offsets:
            paths_a2m.append(base_a2m.copy().shift(offset))
            paths_m2b.append(base_m2b.copy().shift(offset))

        # Spawn p, α, x under Alice on their respective paths
        for val, path in zip(moving_values, paths_a2m):
            self.spawn_payload_at(val, path.get_start(), run_time=0.4)

        self.wait(0.2)

        # Alice → MITM with LaggedStart
        self.play(
            LaggedStart(
                *[
                    MoveAlongPath(val, path)
                    for val, path in zip(moving_values, paths_a2m)
                ],
                lag_ratio=0.05,  # 0.05 * 2s = 0.1s between starts if run_time=2
                run_time=2.0,
            )
        )

        self.wait(0.4)  # pause under MITM

        # ------------------------------------------------------------
        # 4) At MITM, turn x into A and create "Public values" scratchpad
        # ------------------------------------------------------------

        p_pub = MathTex(r"p = 7", font_size=34)
        alpha_pub = MathTex(r"\alpha = 3", font_size=34)
        A_pub = MathTex(r"A = 2", font_size=34)

        # Hidden placeholder for B in MITM's view of public values
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

        # ------------------------------------------------------------
        # 5) Move p, α, A (the three values under MITM) over to Bob
        # ------------------------------------------------------------

        # At this point, under MITM we have:
        # - p_move (p)
        # - alpha_move (α)
        # - A_move
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

        # ------------------------------------------------------------
        # 7) Replace values under Bob with B, send B back to MITM
        # ------------------------------------------------------------

        # Remove the three values p, α, A that are under Bob
        self.play(
            FadeOut(p_move),
            FadeOut(alpha_move),
            FadeOut(A_move),
            run_time=0.5,
        )
        self.wait(0.2)

        # Create a single B message under Bob
        B_move = MathTex(r"B = 5", font_size=34)

        # Use the central Bob → MITM bottom path
        bob_to_mitm_path = self.bob_to_mitm_path

        self.spawn_payload_at(
            B_move,
            bob_to_mitm_path.get_start(),
            run_time=0.4,
        )

        # Bob → MITM (B travelling)
        self.play(MoveAlongPath(B_move, bob_to_mitm_path), run_time=2.0)
        self.wait(0.4)

        # ------------------------------------------------------------
        # 8) Reveal B in MITM's scratchpad, then send B to Alice
        # ------------------------------------------------------------

        # Unhide B_pub in "Public values" scratchpad
        self.play(
            B_pub.animate.set_opacity(1).set_stroke(opacity=1),
            run_time=0.6,
        )
        self.wait(0.4)

        # Now send B from MITM to Alice
        mitm_to_alice_path = self.mitm_to_alice_path

        self.play(MoveAlongPath(B_move, mitm_to_alice_path), run_time=2.0)
        self.wait(0.4)

        self.play(FadeOut(B_move), run_time=0.4)

        self.wait(1.0)

        # ------------------------------------------------------------
        # 9) MITM brute-forces Alice's secret exponent x
        # ------------------------------------------------------------

        # Position near bottom centre
        base_y = -1

        # --- Line 1: try x = 1 ---
        line1 = MathTex(
            r"x = 1 \;\;\Rightarrow\;\; \alpha^1 = 3 \equiv 3 \pmod{7}", font_size=30
        ).move_to([0, base_y, 0])

        self.play(Write(line1), run_time=1.5)
        self.wait(0.3)

        # Add a red cross at the end
        cross1 = MathTex(r"\times", color=RED, font_size=34)
        cross1.next_to(line1, RIGHT, buff=0.4)

        self.play(FadeIn(cross1), run_time=0.5)
        self.wait(0.6)

        # --- Line 2: try x = 2 ---
        line2 = MathTex(
            r"x = 2 \;\;\Rightarrow\;\; \alpha^2 = 9 \equiv 2 \pmod{7}", font_size=30
        ).move_to([0, base_y - 0.5, 0])

        self.play(Write(line2), run_time=1.5)
        self.wait(0.3)

        # Add green tick
        tick2 = MathTex(r"\checkmark", color=GREEN, font_size=34)
        tick2.next_to(line2, RIGHT, buff=0.4)

        self.play(FadeIn(tick2), run_time=0.5)
        self.wait(0.8)

        # --- Line 3: x line ---
        x_line = MathTex(r"x = 2", font_size=30).move_to([0, base_y - 1, 0])

        self.play(Write(x_line), run_time=1.0)
        self.wait(1.0)

        # --- Line 4: Find K ---
        final_line = MathTex(r"K = 5^2 \equiv 4\pmod{7} ", font_size=30).move_to(
            [0, base_y - 1.5, 0]
        )

        self.play(Write(final_line), run_time=1.0)
        self.wait(1.0)


class DH5(NetworkScene):
    def construct(self):
        # Optionally shift scene if needed
        # self.camera.frame.shift(DOWN * 0.2)

        # Alice, MITM, Bob present (no CA)
        self.setup_layout(
            show_alice=True,
            show_mitm=True,
            show_bob=True,
            show_ca=False,
            show_ab_links=True,
            show_ca_links=False,
        )

        self.wait(0.3)

        # ------------------------------------------------------------
        # 1) Build bottom paths: Alice ↔ MITM ↔ Bob
        # ------------------------------------------------------------
        self.build_ab_paths(offset_down=1.5)

        base_a2m = self.alice_to_mitm_path
        base_m2a = self.mitm_to_alice_path
        base_m2b = self.mitm_to_bob_path
        base_b2m = self.bob_to_mitm_path

        # Stack three values vertically using shifted copies of the base paths
        vertical_offsets = [UP * 0.4, ORIGIN, DOWN * 0.4]

        # ------------------------------------------------------------
        # 2) p, α, A appear under Alice, stacked, then go to MITM
        # ------------------------------------------------------------

        # Moving versions
        p_move = MathTex(r"p", font_size=34)
        alpha_move = MathTex(r"\alpha", font_size=34)
        A_move = MathTex(r"A", font_size=34)

        moving_values = [p_move, alpha_move, A_move]

        # Build per-value paths Alice→MITM and MITM→Bob
        paths_a2m = []
        paths_m2b = []

        for offset in vertical_offsets:
            paths_a2m.append(base_a2m.copy().shift(offset))
            paths_m2b.append(base_m2b.copy().shift(offset))

        # Spawn p, α, A under Alice on their respective paths
        for val, path in zip(moving_values, paths_a2m):
            self.spawn_payload_at(val, path.get_start(), run_time=0.4)

        self.wait(0.2)

        # Alice → MITM with LaggedStart
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

        self.wait(0.5)  # pause under MITM

        # ------------------------------------------------------------
        # 3) MITM stores shared key K_A in its scratchpad ("Keys;")
        #    Reserve space for K_B on the top row (initially invisible).
        # ------------------------------------------------------------

        K_B_mitm = MathTex(r"K_B", font_size=34)
        K_B_mitm.set_opacity(0)
        K_B_mitm.set_stroke(opacity=0)

        K_A_mitm = MathTex(r"K_A", font_size=34)

        self.render_scratchpad(
            actor_name="mitm",
            title_text="Keys;",
            # K_B row (top) is reserved but invisible at first
            items=[K_A_mitm, K_B_mitm],
            buff=0.2,
        )

        self.wait(0.5)

        # ------------------------------------------------------------
        # 4) MITM sends forged B back to Alice (who thinks it is Bob's)
        # ------------------------------------------------------------

        B_to_alice = MathTex(r"B", font_size=34)

        self.spawn_payload_at(
            B_to_alice,
            base_m2a.get_start(),
            run_time=0.4,
        )

        # MITM → Alice: B travelling
        self.play(MoveAlongPath(B_to_alice, base_m2a), run_time=2.0)
        self.wait(0.4)

        # Alice "processes" B
        self.play(FadeOut(B_to_alice), run_time=0.4)
        self.wait(0.3)

        # ------------------------------------------------------------
        # 5) Alice stores K_A in her own scratchpad ("Keys;")
        # ------------------------------------------------------------

        K_A_alice = MathTex(r"K_A", font_size=34)

        self.render_scratchpad(
            actor_name="alice",
            title_text="Keys;",
            items=[K_A_alice],
            buff=0.2,
        )

        self.wait(0.7)

        # ------------------------------------------------------------
        # 6) MITM sends p, α, A on to Bob (same triple, now MITM→Bob)
        # ------------------------------------------------------------

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

        # ------------------------------------------------------------
        # 7) Bob computes and stores K_B in his scratchpad ("Keys;")
        # ------------------------------------------------------------

        K_B_bob = MathTex(r"K_B", font_size=34)

        self.render_scratchpad(
            actor_name="bob",
            title_text="Keys;",
            items=[K_B_bob],
            buff=0.2,
        )

        self.wait(0.7)

        # ------------------------------------------------------------
        # 8) Bob sends B back to MITM, who then reveals K_B on top row
        # ------------------------------------------------------------

        B_to_mitm = MathTex(r"B", font_size=34)

        self.spawn_payload_at(
            B_to_mitm,
            base_b2m.get_start(),
            run_time=0.4,
        )

        # Bob → MITM: B travelling
        self.play(MoveAlongPath(B_to_mitm, base_b2m), run_time=2.0)
        self.wait(0.4)

        # MITM now "learns" K_B and reveals its row
        self.play(
            K_B_mitm.animate.set_opacity(1).set_stroke(opacity=1),
            run_time=0.6,
        )
        self.wait(0.3)

        # Optionally remove travelling B after processing
        self.play(FadeOut(B_to_mitm), run_time=0.4)

        self.wait(1.0)


class DH6(NetworkScene):
    def construct(self):

        self.camera.frame.shift(UP * 0.2)

        # Alice, MITM, Bob present (no CA)
        self.setup_layout(
            show_alice=True,
            show_mitm=True,
            show_bob=True,
            show_ca=False,
            show_ab_links=True,
            show_ca_links=False,
        )

        self.wait(0.3)

        # ------------------------------------------------------------
        # 1) Build bottom paths: Alice ↔ MITM ↔ Bob
        # ------------------------------------------------------------

        self.build_ab_paths(offset_down=1.5)

        base_a2m = self.alice_to_mitm_path
        base_m2b = self.mitm_to_bob_path
        base_b2m = self.bob_to_mitm_path

        # We will stack three values vertically using shifted copies of the base paths
        vertical_offsets = [UP * 0.4, DOWN * 0.8]

        # ------------------------------------------------------------
        # 2) Bob knows PU_A
        # ------------------------------------------------------------

        self.wait(0.5)

        PU_A = MathTex(r"PU_A", font_size=28)

        self.render_scratchpad(
            actor_name="bob",
            title_text="Keyvault:",
            items=[PU_A],
            buff=0.4,
        )

        self.wait(0.5)

        # ------------------------------------------------------------
        # 2) p, α, x appear under Alice, stacked, then go to MITM
        # ------------------------------------------------------------

        # Moving versions (separate from scratchpad items)
        public_vals = MathTex(r"(p = 7, \alpha = 3, A = 2)", font_size=32)
        repeat_vals = MathTex(r"(p = 7, \alpha = 3, A = 2)", font_size=32)

        moving_values = [public_vals, repeat_vals]

        # Build per-value paths Alice→MITM and MITM→Bob
        paths_a2m = []
        paths_m2b = []
        paths_b2m = []

        for offset in vertical_offsets:
            paths_a2m.append(base_a2m.copy().shift(offset))
            paths_m2b.append(base_m2b.copy().shift(offset))
            paths_b2m.append(base_b2m.copy().shift(offset))

        # Spawn p, α, x under Alice on their respective paths
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

        ## Alice → MITM with LaggedStart
        self.play(
            LaggedStart(
                *[
                    MoveAlongPath(val, path)
                    for val, path in zip(moving_values, paths_a2m)
                ],
                lag_ratio=0.05,  # 0.05 * 2s = 0.1s between starts if run_time=2
                run_time=2.0,
            )
        )

        self.wait(0.4)  # pause under MITM

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

        # Add green tick
        tick2 = MathTex(r"\checkmark", color=GREEN, font_size=40)
        tick2.next_to(repeat_vals, RIGHT, buff=0.4)

        self.play(FadeIn(tick2), run_time=0.5)
        self.wait(0.8)

        # reverse to get back to MITM

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

        # Now change values and try again

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

        # from mitm to bob again

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

        # Add red cross
        cross = MathTex(r"\times", color=RED, font_size=40)
        cross.next_to(repeat_vals, RIGHT, buff=0.4)

        self.play(FadeIn(cross), run_time=0.5)
        self.wait(0.8)


class DH8(NetworkScene):
    def construct(self):

        self.camera.frame.shift(UP * 1)

        # All actors present, CA + CA-links animate in
        self.setup_layout(
            show_alice=True,
            show_mitm=True,
            show_bob=True,
            show_ca=True,
            show_ab_links=True,  # Alice–MITM–Bob bottom line
            show_ca_links=True,  # Alice–CA and Bob–CA diagonals
            animate_actors=["ca"],  # CA fades in
            animate_links=["alice_ca", "bob_ca"],  # only CA links animate
        )

        self.wait(0.3)

        # Animate CA + its links
        self.animate_entrance(run_time=0.8)
        self.wait(0.3)

        # ------------------------------------------------------------
        # 1) Alice's key scratchpad ("Keys;") with PU_A and PR_A
        #    using your left_shift / down_shift convention
        # ------------------------------------------------------------

        PU_A = MathTex(r"PU_A", font_size=30)
        PR_A = MathTex(r"PR_A", font_size=30)

        # Hidden placeholder for Bob's public value B (blank row for now)
        Ka_sp = MathTex(r"K", font_size=30)
        Ka_sp.set_opacity(0)
        Ka_sp.set_stroke(opacity=0)

        self.render_scratchpad(
            actor_name="alice",
            title_text="Keys;",
            items=[PU_A, PR_A, Ka_sp],
            buff=0.4,
            left_shift=2,  # you mentioned this in your updated version
            down_shift=2,  # (left and down for Alice)
        )

        self.wait(0.6)

        # ------------------------------------------------------------
        # 2) Build Alice ↔ CA paths and stack TWO paths vertically
        #    Top:  plaintext  (PU_A, "Alice")
        #    Bottom: signed/hash, boxed in green
        # ------------------------------------------------------------

        # Build the base Alice–CA path
        self.build_ca_paths()
        base_a2ca = self.alice_to_ca_path

        # Two vertically offset paths: top & bottom
        vertical_offsets = [UP * 1.2 + LEFT * 0.4, UP * 0.3 + LEFT * 0.4]

        paths_a2ca = [base_a2ca.copy().shift(offset) for offset in vertical_offsets]

        # ------------------------------------------------------------
        # 3) Render plaintext payload above, and a second copy below
        # ------------------------------------------------------------

        # Plaintext: (PU_A, "Alice")
        plain_payload = MathTex(
            r"(PU_A, \text{Alice})",
            font_size=32,
        )

        # Second copy that we'll turn into hex "signature"
        signed_payload = MathTex(
            r"(PU_A, \text{Alice})",
            font_size=32,
        )

        moving_values = [plain_payload, signed_payload]

        # Spawn them at the start of their respective Alice→CA paths
        for val, path in zip(moving_values, paths_a2ca):
            self.spawn_payload_at(val, path.get_start(), run_time=0.6)

        self.wait(0.4)

        # ------------------------------------------------------------
        # 4) Turn the lower one into "hash-like" hex and box it
        # ------------------------------------------------------------

        hex_signature = MathTex(
            r"\texttt{ba7816bf8e\dots}",  # gibberish hex, visually a hash
            font_size=32,
        ).move_to(signed_payload)

        # Transform bottom copy into the hexy "signature"
        self.play(Transform(signed_payload, hex_signature), run_time=0.6)

        # Green box around the hex (signature)
        sig_box = SurroundingRectangle(
            signed_payload,
            buff=0.3,
            color=GREEN,
        )
        self.play(Create(sig_box), run_time=0.6)

        # Group the signed payload + box so they move together
        signed_group = VGroup(signed_payload, sig_box)

        # Replace in moving_values so index 1 is the grouped signed object
        moving_values[1] = signed_group

        self.wait(0.4)

        # ------------------------------------------------------------
        # 5) Send BOTH: plaintext (top) and signed (bottom) to CA
        # ------------------------------------------------------------

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

        # ------------------------------------------------------------
        # 6) CA verifies Alice's signature (hash + compare)
        # ------------------------------------------------------------

        # 6.1 "Unwrap" the signature: remove the green box, keep the hex text
        self.play(FadeOut(sig_box), run_time=0.4)
        self.wait(0.2)

        # 6.2 CA recomputes the hash from the plaintext payload
        ca_hash = MathTex(
            r"\texttt{ba7816bf8e\dots}",
            font_size=32,
        ).move_to(plain_payload)

        self.play(Transform(plain_payload, ca_hash), run_time=0.6)
        self.wait(0.2)

        # 6.3 Add green tick to show the two hashes match
        ca_tick = MathTex(r"\checkmark", color=GREEN, font_size=40)
        ca_tick.next_to(plain_payload, RIGHT, buff=0.4)

        self.play(FadeIn(ca_tick), run_time=0.5)
        self.wait(0.6)

        # 6.4 Clear verification artifacts from the screen
        self.play(
            FadeOut(plain_payload),
            FadeOut(signed_payload),
            FadeOut(ca_tick),
            run_time=0.6,
        )
        self.wait(0.4)

        # ------------------------------------------------------------
        # 7) CA creates a certificate + signature and sends it to Alice
        # ------------------------------------------------------------

        # Base CA→Alice path and vertically stacked copies (reuse vertical_offsets)
        base_ca2a = self.ca_to_alice_path
        cert_paths_ca2a = [
            base_ca2a.copy().shift(offset) for offset in vertical_offsets
        ]

        # 7.1 Plain certificate content (hash over PU_A, Alice, Demo CA)
        cert_plain = MathTex(
            r"(PU_A, \text{Alice}, \text{Demo CA})",
            font_size=32,
        )

        # 7.2 Signed hash (random hex) that CA produces
        cert_plain_copy = MathTex(
            r"(PU_A, \text{Alice}, \text{Demo CA})",
            font_size=32,
        )

        cert_values = [cert_plain, cert_plain_copy]

        # Spawn them at the CA end of their respective CA→Alice paths
        for val, path in zip(cert_values, cert_paths_ca2a):
            self.spawn_payload_at(val, path.get_start(), run_time=0.6)

        self.wait(0.4)

        cert_sig_text = MathTex(
            r"\texttt{9af13c42b\dots}",
            font_size=32,
        ).move_to(cert_plain_copy)

        # Transform bottom copy into the hexy "signature"
        self.play(Transform(cert_plain_copy, cert_sig_text), run_time=0.6)

        # Yellow box around the signature to indicate "signed by CA"
        cert_sig_box = SurroundingRectangle(
            cert_plain_copy,
            buff=0.3,
            color=YELLOW,
        )
        self.play(Create(cert_sig_box), run_time=0.6)

        cert_sig_group = VGroup(cert_plain_copy, cert_sig_box)
        cert_values[1] = cert_sig_group

        # 7.3 Send certificate + CA signature down to Alice
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

        # ------------------------------------------------------------
        # 8) Alice sends (p, α, A), signed copy, and CERT_A via MITM to Bob
        #     Top:   (p = 7, α = 3, A = 2)
        #     Middle: same, but hashed + green box (signature)
        #     Bottom: CERT_A
        # ------------------------------------------------------------

        # Build bottom paths for Alice ↔ MITM ↔ Bob
        self.build_ab_paths(offset_down=1.5)

        base_a2m = self.alice_to_mitm_path
        base_m2b = self.mitm_to_bob_path

        # Three stacked lanes: top, middle, bottom
        triple_offsets = [UP * 0.5, DOWN * 0.15, DOWN * 0.8]

        paths_a2m_triple = [base_a2m.copy().shift(off) for off in triple_offsets]
        paths_m2b_triple = [base_m2b.copy().shift(off) for off in triple_offsets]

        # ---------- 8.1 Three payloads stacked above Alice ----------

        # Top: plain DH public values
        dh_plain = MathTex(
            r"(p = 7, \alpha = 3, A = 2)",
            font_size=30,
        )

        # Middle: same values, will become hex + green box
        dh_signed = MathTex(
            r"(p = 7, \alpha = 3, A = 2)",
            font_size=30,
        )

        # Bottom: CERT_A label
        cert_A = MathTex(
            r"CERT_A",
            font_size=30,
        )

        triple_values = [dh_plain, dh_signed, cert_A]

        # Spawn all three at the Alice→MITM path starts
        for val, path in zip(triple_values, paths_a2m_triple):
            self.spawn_payload_at(val, path.get_start(), run_time=0.6)

        self.wait(0.4)

        # ---------- 8.2 Turn middle into hex "signature" + green box ----------

        dh_hex = MathTex(
            r"\texttt{ba7816bf8e\dots}",
            font_size=32,
        ).move_to(dh_signed)

        # Transform middle copy into the hash-like hex
        self.play(Transform(dh_signed, dh_hex), run_time=0.6)

        sig_box2 = SurroundingRectangle(
            dh_signed,
            buff=0.3,
            color=GREEN,
        )
        self.play(Create(sig_box2), run_time=0.6)

        # Move text + box together
        signed_group2 = VGroup(dh_signed, sig_box2)
        triple_values[1] = signed_group2

        self.wait(0.4)

        # ---------- 8.3 Alice → MITM ----------

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

        # ---------- 8.4 MITM → Bob ----------

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

        # ------------------------------------------------------------
        # 9) Bob verifies CERT_A and the DH signature
        # ------------------------------------------------------------

        # 9.1 Tick next to CERT_A to show he trusts the certificate
        cert_tick = MathTex(r"\checkmark", color=GREEN, font_size=36)
        cert_tick.next_to(cert_A, RIGHT, buff=0.2)

        self.play(FadeIn(cert_tick), run_time=0.4)
        self.wait(0.3)

        # 9.2 "Unwrap" the signature: remove the green box, keep the hex text
        self.play(FadeOut(sig_box2), run_time=0.4)
        self.wait(0.2)

        # 9.3 Bob recomputes the hash from the plaintext DH values
        bob_hash = MathTex(
            r"\texttt{ba7816bf8e\dots}",
            font_size=32,
        ).move_to(dh_plain)

        self.play(Transform(dh_plain, bob_hash), run_time=0.6)
        self.wait(0.2)

        # 9.4 Add green tick to show the two hashes match
        sig_tick = MathTex(r"\checkmark", color=GREEN, font_size=36)
        sig_tick.next_to(dh_plain, RIGHT, buff=0.2)

        self.play(FadeIn(sig_tick), run_time=0.4)
        self.wait(0.8)

        # ------------------------------------------------------------
        # 9) Clear Bob's local DH/CERT view so we can re-do the flow from Bob's side
        # ------------------------------------------------------------

        self.play(
            FadeOut(dh_plain),
            FadeOut(dh_signed),
            FadeOut(cert_A),
            # comment these out if you have not added them yet:
            FadeOut(cert_tick),
            FadeOut(sig_tick),
            run_time=0.6,
        )
        self.wait(0.4)

        # ------------------------------------------------------------
        # 10) Bob's key scratchpad ("Keys;") with PU_B, PR_B, and K
        #     (shifted to the RIGHT and slightly down)
        # ------------------------------------------------------------

        PU_B = MathTex(r"PU_B", font_size=30)
        PR_B = MathTex(r"PR_B", font_size=30)
        K_B = MathTex(r"K", font_size=30)

        self.render_scratchpad(
            actor_name="bob",
            title_text="Keys;",
            items=[PU_B, PR_B, K_B],
            buff=0.4,
            left_shift=-2,  # negative = shift right, mirroring Alice
            down_shift=2,
        )

        self.wait(0.6)

        # ------------------------------------------------------------
        # 11) Bob sends (PU_B, "Bob") + signed version to CA (blue box)
        # ------------------------------------------------------------

        # Rebuild CA paths to be safe
        self.build_ca_paths()

        base_b2ca = self.bob_to_ca_path

        # Two vertically offset paths to the CA (to the right of the line)
        vertical_offsets_bob = [UP * 3 + RIGHT * 1.2, UP * 2.1 + RIGHT * 1.2]
        paths_b2ca = [base_b2ca.copy().shift(off) for off in vertical_offsets_bob]

        # Plaintext: (PU_B, "Bob")
        plain_payload_B = MathTex(
            r"(PU_B, \text{Bob})",
            font_size=32,
        )

        # Second copy that will become hex (Bob's signature)
        signed_payload_B = MathTex(
            r"(PU_B, \text{Bob})",
            font_size=32,
        )

        moving_values_B = [plain_payload_B, signed_payload_B]

        # Spawn them at the start of the Bob→CA paths
        for val, path in zip(moving_values_B, paths_b2ca):
            self.spawn_payload_at(val, path.get_start(), run_time=0.6)

        self.wait(0.4)

        # Turn the lower one into hex-like "signature" and add BLUE box
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

        # Send BOTH (plain + signed) from Bob to CA
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

        # ------------------------------------------------------------
        # 12) CA verifies Bob's signature (hash + compare)
        # ------------------------------------------------------------

        # Remove the BLUE box, keep the hex text
        self.play(FadeOut(sig_box_B), run_time=0.4)
        self.wait(0.2)

        # CA recomputes the hash from the plaintext Bob payload
        ca_hash_B = MathTex(
            r"\texttt{c4d29af7e\dots}",
            font_size=32,
        ).move_to(plain_payload_B)

        self.play(Transform(plain_payload_B, ca_hash_B), run_time=0.6)
        self.wait(0.2)

        # Green tick to show hashes match
        ca_tick_B = MathTex(r"\checkmark", color=GREEN, font_size=40)
        ca_tick_B.next_to(plain_payload_B, RIGHT, buff=0.4)

        self.play(FadeIn(ca_tick_B), run_time=0.5)
        self.wait(0.6)

        # Clear these verification artefacts
        self.play(
            FadeOut(plain_payload_B),
            FadeOut(signed_payload_B),
            FadeOut(ca_tick_B),
            run_time=0.6,
        )
        self.wait(0.4)

        # ------------------------------------------------------------
        # 13) CA creates Bob's certificate + signature and sends it to Bob
        # ------------------------------------------------------------

        base_ca2b = self.ca_to_bob_path
        cert_paths_ca2b = [base_ca2b.copy().shift(off) for off in vertical_offsets_bob]

        # Certificate content for Bob
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
            color=YELLOW,  # CA's signature colour stays as your Alice case
        )
        self.play(Create(cert_sig_box_B), run_time=0.6)

        cert_sig_group_B = VGroup(cert_plain_B_copy, cert_sig_box_B)
        cert_values_B[1] = cert_sig_group_B

        # Send certificate + CA signature down to Bob
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

        # (Optional) fade out the certificate payloads at Bob after he "stores" them
        self.play(FadeOut(*[elem for elem in cert_values_B]), run_time=1.0)
        self.wait(0.4)

        # ------------------------------------------------------------
        # 14) Bob sends (p, α, B), signed copy (blue), and CERT_B via MITM to Alice
        # ------------------------------------------------------------

        self.build_ab_paths(offset_down=1.5)

        base_b2m = self.bob_to_mitm_path
        base_m2a = self.mitm_to_alice_path

        triple_offsets_B = [UP * 0.5, DOWN * 0.15, DOWN * 0.8]

        paths_b2m_triple = [base_b2m.copy().shift(off) for off in triple_offsets_B]
        paths_m2a_triple = [base_m2a.copy().shift(off) for off in triple_offsets_B]

        # Top: plain DH values from Bob (with B)
        dh_plain_B = MathTex(
            r"(p = 7, \alpha = 3, B = 5)",
            font_size=30,
        )

        # Middle: same values, to become hex + BLUE box
        dh_signed_B = MathTex(
            r"(p = 7, \alpha = 3, B = 5)",
            font_size=30,
        )

        # Bottom: CERT_B label
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


# VVV Examples VVV


# class AliceToBob(NetworkScene):
#     def construct(self):
#         self.setup_layout(
#             show_alice=True,
#             show_mitm=True,
#             show_bob=True,
#             show_ca=False,
#             show_ab_links=True,
#             show_ca_links=False,
#         )

#         # Build the offset bottom paths for Alice–MITM–Bob
#         self.build_ab_paths(offset_down=1.5)

#         self.wait(0.5)

#         # Packet starts under Alice on the offset path
#         packet = self.make_packet_at(self.alice_to_mitm_path.get_start())

#         # Alice → MITM
#         self.play(MoveAlongPath(packet, self.alice_to_mitm_path), run_time=2)
#         self.wait(0.5)

#         # MITM → Bob (same packet, continuous, still below)
#         self.play(MoveAlongPath(packet, self.mitm_to_bob_path), run_time=2)
#         self.wait(1)


# # ---------- Scene 2: Alice ↔ CA (as before) ----------


# class AliceToCA(NetworkScene):
#     def construct(self):
#         self.setup_layout(
#             show_alice=True,
#             show_mitm=True,
#             show_bob=True,
#             show_ca=True,
#             show_ab_links=True,
#             show_ca_links=True,
#         )
#         self.build_ca_paths()

#         self.wait(0.5)

#         packet = self.make_packet_at(self.alice_to_ca_path.get_start())
#         self.play(MoveAlongPath(packet, self.alice_to_ca_path), run_time=2)
#         self.wait(0.5)

#         packet.move_to(self.ca_to_alice_path.get_start())
#         self.play(MoveAlongPath(packet, self.ca_to_alice_path), run_time=2)
#         self.wait(1)


# # ---------- NEW Scene 3: Direct Alice ↔ Bob (no MITM) ----------


# class AliceBobDirect(NetworkScene):
#     def construct(self):
#         self.setup_layout(
#             show_alice=True,
#             show_mitm=False,
#             show_bob=True,
#             show_ca=False,
#             show_ab_links=True,
#             show_ca_links=False,
#         )
#         self.build_ab_paths(offset_down=1.5)

#         self.wait(0.5)

#         # Classic LaTeX-style text payload
#         msg = Text("Hello Bob", font_size=32)

#         # Start it at the beginning of the path
#         msg.move_to(self.alice_to_bob_path.get_start())
#         self.add(msg)

#         # Move along your existing path
#         self.play(MoveAlongPath(msg, self.alice_to_bob_path), run_time=2)
#         self.wait(1)


# class CScene(NetworkScene):
#     def construct(self):
#         self.setup_layout(
#             show_alice=True,
#             show_mitm=False,
#             show_bob=True,
#             show_ca=False,
#             show_ab_links=True,
#             show_ca_links=False,
#         )
#         self.build_ab_paths(offset_down=1.5)

#         self.wait(0.5)

#         # 1) Create a circle payload (instead of the red square packet)
#         circle = Circle(radius=0.3, fill_opacity=1.0, color=BLUE)
#         # put it at the start of the Alice→Bob path (under Alice)
#         circle.move_to(self.alice_to_bob_path.get_start())
#         self.add(circle)

#         # 2) Move Alice → Bob
#         self.play(MoveAlongPath(circle, self.alice_to_bob_path), run_time=2)
#         self.wait(0.5)

#         # 3) Move Bob → Alice (same object, no disappear/reappear)
#         self.play(MoveAlongPath(circle, self.bob_to_alice_path), run_time=2)
#         self.wait(1)


# class IntroduceCA(NetworkScene):
#     def construct(self):
#         self.setup_layout(
#             show_alice=True,
#             show_mitm=True,
#             show_bob=True,
#             show_ca=True,
#             show_ab_links=True,
#             show_ca_links=True,
#             animate_actors=["ca"],  # CA appears via animation
#             animate_links=["alice_ca", "bob_ca"],  # slanted links appear via animation
#         )

#         # Existing actors/links (Alice, MITM, Bob, bottom links) are already on screen
#         self.wait(0.5)

#         # Animate in CA + its links
#         self.animate_entrance(run_time=1.0)

#         self.wait(0.5)

#         # Now you can build and use CA paths as normal
#         self.build_ca_paths()

#         packet = self.make_packet_at(self.alice_to_ca_path.get_start(), label="CSR")
#         self.play(MoveAlongPath(packet, self.alice_to_ca_path), run_time=2)
#         self.wait(1)


# class StackedMessages(NetworkScene):
#     def construct(self):
#         self.setup_layout(
#             show_alice=True,
#             show_mitm=False,
#             show_bob=True,
#             show_ca=False,
#             show_ab_links=True,
#             show_ca_links=False,
#         )
#         self.build_ab_paths(offset_down=1.5)

#         self.wait(0.5)

#         base_path = self.alice_to_bob_path

#         # Message A: classic LaTeX text on the base path
#         msg_a = MathTex("Hi Bob", font_size=32)
#         self.spawn_payload_at(msg_a, base_path.get_start())  # entrance anim

#         # Message B: another text, offset slightly down using a shifted path
#         offset_path = base_path.copy().shift(DOWN * 0.7)
#         msg_b = MathTex("Packet", font_size=32)
#         self.spawn_payload_at(msg_b, offset_path.get_start())  # entrance anim

#         # Move both together along their paths
#         self.play(
#             LaggedStart(
#                 MoveAlongPath(msg_a, base_path),
#                 MoveAlongPath(msg_b, offset_path),
#                 lag_ratio=0.02,  # 0.05 * 2s = 0.1s between starts
#                 run_time=2,
#             )
#         )
#         self.wait(1)


# class AliceBobUpdateDemo(NetworkScene):
#     def construct(self):
#         # Just Alice and Bob, with the direct link + bottom paths
#         self.setup_layout(
#             show_alice=True,
#             show_mitm=False,
#             show_bob=True,
#             show_ca=False,
#             show_ab_links=True,
#             show_ca_links=False,
#         )
#         self.build_ab_paths(offset_down=1.5)

#         self.wait(0.5)

#         base_path = self.alice_to_bob_path

#         # 1) Spawn a payload under Alice (this can be MathTex, Text, a circle, etc.)
#         msg = MathTex(r"\text{Hello, Bob!}", font_size=36)
#         self.spawn_payload_at(msg, base_path.get_start(), run_time=0.6)

#         # 2) Move Alice → Bob
#         self.play(MoveAlongPath(msg, base_path), run_time=2)
#         self.wait(0.3)

#         # 3) "Update" the object by adding a containing rectangle around it
#         #    (and animate the rectangle appearing)
#         highlight = SurroundingRectangle(msg, buff=0.2, color=YELLOW)
#         self.play(Create(highlight), run_time=0.6)

#         # Optionally pause to show the updated state
#         self.wait(0.3)

#         # 4) Move the *combined* object (msg + rectangle) back Bob → Alice
#         wrapped = VGroup(msg, highlight)

#         self.play(
#             MoveAlongPath(wrapped, self.bob_to_alice_path),
#             run_time=2,
#         )

#         self.wait(1)


# class AliceBobChangeMessage(NetworkScene):
#     def construct(self):
#         self.setup_layout(
#             show_alice=True,
#             show_mitm=False,
#             show_bob=True,
#             show_ca=False,
#             show_ab_links=True,
#             show_ca_links=False,
#         )
#         self.build_ab_paths(offset_down=1.5)

#         self.wait(0.5)
#         base_path = self.alice_to_bob_path

#         # 1) Spawn initial message under Alice
#         msg = MathTex(r"\text{Hello, Bob!}", font_size=36)
#         self.spawn_payload_at(msg, base_path.get_start(), run_time=0.6)

#         # 2) Alice → Bob
#         self.play(MoveAlongPath(msg, base_path), run_time=2)
#         self.wait(0.3)

#         # 3) CHANGE THE MESSAGE CONTENT AT BOB
#         new_msg = MathTex(r"\text{Got your message.}", font_size=36)

#         # keep the new text in the same place as the old one
#         new_msg.move_to(msg.get_center())

#         # animated change
#         self.play(Transform(msg, new_msg), run_time=0.6)
#         self.wait(0.3)

#         # 4) Send the updated message Bob → Alice
#         self.play(MoveAlongPath(msg, self.bob_to_alice_path), run_time=2)
#         self.wait(1)
