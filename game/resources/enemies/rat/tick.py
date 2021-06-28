global POWER
if self.state == 1:
    POWER -= 0.035 * self.difficulty
elif self.state == 0:
    if random.randint(0, 35) - self.difficulty <= 0:
        self.state = 1
        self.visible = True
        self.current_room = random.choice(self.path)
