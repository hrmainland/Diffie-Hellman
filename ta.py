from manim import *

class Ta(Scene):
    def construct(self):
        equation = MathTex("y = 17")
        self.play(Write(equation))
        self.wait(2)
