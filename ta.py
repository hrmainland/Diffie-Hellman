from manim import *


class Ta(Scene):
    def construct(self):
        # Create labels
        alice_text = Text("Alice")
        bob_text = Text("Bob")

        # Create boxes around the labels
        alice_box = SurroundingRectangle(alice_text, buff=0.3)
        bob_box = SurroundingRectangle(bob_text, buff=0.3)

        # Group text + box together so they move as one
        alice_group = VGroup(alice_box, alice_text).shift(LEFT * 3)
        bob_group = VGroup(bob_box, bob_text).shift(RIGHT * 3)

        # 1) Alice appears (box + label)
        self.play(FadeIn(alice_group))
        self.wait(0.5)

        # 2) Bob appears (box + label)
        self.play(FadeIn(bob_group))
        self.wait(0.5)

        # 3) Draw a line between the right edge of Alice's box
        #    and the left edge of Bob's box
        connection_line = Line(alice_box.get_right(), bob_box.get_left())

        self.play(Create(connection_line))
        self.wait(1)
