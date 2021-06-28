import pygame as pg
import json
import random
import queue
import sys
import time


class Button:
    def __init__(self, button_id, location=None, target=None, args=(), relative=False):
        self.id = button_id
        self.target = target
        self.args = args
        self.data = get_info(button_id)
        if location is not None:
            self.location = location
        else:
            self.location = self.data.location
        self.sprite = pg.image.load(self.data.images[0]).convert_alpha()
        self.pressed_sprite = pg.image.load(self.data.images[1]).convert_alpha()
        self.pressed = False
        self.rect = self.sprite.get_rect()
        self.rect.topleft = self.location
        self.relative = relative

    def draw(self, surface: pg.Surface):
        if self.relative:
            location = get_actual_pos(self.location, VIEWPORT)
        else:
            location = self.location
        if not self.pressed:
            surface.blit(self.sprite, location)
        else:
            surface.blit(self.pressed_sprite, location)

    def __repr__(self):
        return f"Button: (id: {self.id}, location: {self.location})"

    def __bool__(self):
        return self.pressed

    def get_presssed(self):
        if not self.relative and self.rect.collidepoint(pg.mouse.get_pos()):
            self.run()
            if self.pressed:
                self.pressed = False
            else:
                self.pressed = True
        elif self.relative:
            x, y, w, h = self.rect
            test_rect = pg.Rect(x, y, w, h)
            test_rect.topleft = get_actual_pos(self.rect.topleft, VIEWPORT)
            if test_rect.collidepoint(pg.mouse.get_pos()):
                self.run()
                if self.pressed:
                    self.pressed = False
                else:
                    self.pressed = True

    def run(self):
        if self.target is not None:
            self.target(*self.args)


class Data:
    def __init__(self, var_dict: dict):
        for var in var_dict.keys():
            exec(f"self.{var} = var_dict[var]")


class Enemy:
    def __init__(self, enemy_id, difficulty):
        self.id = enemy_id
        self.data = get_info(enemy_id)
        try:
            self.rate = self.data.rate
        except AttributeError:
            self.rate = 1

        self.path = list(self.data.images.keys())
        self.images = self.data.images
        self.difficulty = difficulty

        self.current_room = self.path[0]
        self.state = 0
        self.visible = True

        try:
            with open(self.data.setup) as file:
                exec(file.read())
        except AttributeError:
            pass

    def tick(self):
        if self.current_room not in list(DOORS.keys()):
            if random.randint(0, 40) - self.difficulty > 0 or random.randint(1, MASTER_DIFFICULTY // self.rate) != 1:
                return
        elif not DOORS[self.current_room]:
            if random.randint(0, 40)-self.difficulty//2 > 0 or random.randint(1, MASTER_DIFFICULTY*2 // self.rate) != 1:
                return
        else:
            if random.randint(0, 40) - self.difficulty > 0 or random.randint(1, MASTER_DIFFICULTY // self.rate*2) != 1:
                return
        try:
            with open(self.data.tick) as file:
                exec(file.read())
        except AttributeError:
            self.default_tick()

    def default_tick(self):
        if self.current_room == game.current_camera.name and CAMERA:
            switch_sound = pg.mixer.Sound("resources/enemies/switch.wav")
            switch_sound.play()
        if self.current_room != OFFICE_ROOM:
            if self.current_room in list(DOORS.keys()) and DOORS[self.current_room]:
                self.current_room = self.path[0]
            else:
                self.current_room = self.path[self.path.index(self.current_room) + 1]
        if self.current_room == OFFICE_ROOM:
            JUMPSCARE_QUEUE.put(self)

    def draw(self, surface: pg.Surface, relative=False):
        if self.visible:
            image, location = self.images[self.current_room]
            image = pg.image.load(image).convert_alpha()
            rect = image.get_rect()
            if relative:
                rect.center = get_actual_pos(location, VIEWPORT)
            else:
                rect.center = location
            surface.blit(image, rect)

    def jumpscare(self, surface):
        jumpscare_image = list(self.data.jumpscare_image.keys())[0]
        surface.blit(pg.image.load(jumpscare_image).convert_alpha(), self.data.jumpscare_image[jumpscare_image])
        pg.display.update()
        jumpscare_sound = pg.mixer.Sound("resources/enemies/jumpscasre.wav")
        jumpscare_sound.play()
        time.sleep(5)
        sys.exit()

    def __repr__(self):
        return f"Enemy: (id: {self.id}, difficulty: {self.difficulty}, location: {self.current_room})"


class Room:
    def __init__(self, room_id, buttons=()):
        self.id = room_id
        self.data = get_info(room_id)
        self.image = pg.image.load(self.data.image).convert_alpha()
        self.name = self.data.name

        self.buttons = buttons

    def draw(self, surface):
        surface.blit(self.image, (0, 0))

    def __repr__(self):
        return f"Room: (id: {self.id})"


def get_info(info_id):
    with open(f"resources/{'/'.join(info_id.split(':'))}/data.json") as info_file:
        return Data(json.load(info_file))


def get_actual_pos(pos, viewport_pos):
    _x, _y, w, h = viewport_pos
    x, y = pos
    return x - _x, y - _y


def change_camera(camera_id):
    switch_sound = pg.mixer.Sound("resources/other/camera.wav")
    switch_sound.play()
    for room in game.rooms:
        if room.name == camera_id:
            game.current_camera = room


def toggle_door(door_id):
    if DOORS[door_id] and POWER > 0:
        DOORS[door_id] = False
    else:
        DOORS[door_id] = True


def shock():
    for enemy in game.enemies:
        if enemy.id == "enemies:rat" and enemy.current_room == game.current_camera.name:
            shock_sound = pg.mixer.Sound("resources/other/buttons/shock/shock.wav")
            shock_sound.play()
            enemy.state = 0
            enemy.visible = False


def feed(ammount):
    global FOOD
    FOOD += ammount
    if FOOD > MAX_FOOD:
        FOOD = MAX_FOOD


class Game:
    def __init__(self, level_id):
        self.level = level_id.split(":")[-1]
        self.window = pg.display.set_mode(WINDOW_SIZE)
        self.fps = 30
        self.clock = pg.time.Clock()
        self.rooms = []
        self.enemies = []
        self.camera_buttons = []
        self.room_buttons = []
        self.create_rooms()
        self.data = get_info(level_id)
        self.current_camera = self.rooms[4]
        self.power_mult = self.data.power_mult
        try:
            self.minutes = self.data.minutes
        except AttributeError:
            self.minutes = 6
        pg.font.init()
        self.font = pg.font.SysFont("Comic Sans MS", 48)
        for enemy in self.data.enemies.keys():
            if self.data.enemies[enemy] > 0:
                self.enemies.append(Enemy(enemy, self.data.enemies[enemy]))
        self.main_room_sprite = pg.image.load(get_info("rooms:1e").image_main).convert_alpha()
        pg.mixer.init()

        self.room_buttons.append(
            Button(
                button_id="other:buttons:1d",
                target=toggle_door,
                args=("1d",),
                relative=True
            )
        )

        self.room_buttons.append(
            Button(
                button_id="other:buttons:2d",
                target=toggle_door,
                args=("2d",),
                relative=True
            )
        )

    def create_rooms(self):
        self.rooms.append(Room(
            room_id="rooms:1a"
        ))
        self.camera_buttons.append(Button(
            button_id="other:buttons:1a",
            target=change_camera,
            args=("1a",)
        ))

        self.rooms.append(Room(
            room_id="rooms:2a"
        ))
        self.camera_buttons.append(Button(
            button_id="other:buttons:2a",
            target=change_camera,
            args=("2a",)
        ))

        self.rooms.append(Room(
            room_id="rooms:1b"
        ))
        self.camera_buttons.append(Button(
            button_id="other:buttons:1b",
            target=change_camera,
            args=("1b",)
        ))

        self.rooms.append(Room(
            room_id="rooms:2b"
        ))
        self.camera_buttons.append(Button(
            button_id="other:buttons:2b",
            target=change_camera,
            args=("2b",)
        ))

        self.rooms.append(Room(
            room_id="rooms:1c"
        ))
        self.camera_buttons.append(Button(
            button_id="other:buttons:1c",
            target=change_camera,
            args=("1c",)
        ))

        self.rooms.append(Room(
            room_id="rooms:2c",
            buttons=(Button(
                button_id="other:buttons:feed",
                target=feed,
                args=(5,)
            ),)
        ))
        self.camera_buttons.append(Button(
            button_id="other:buttons:2c",
            target=change_camera,
            args=("2c",)
        ))

        self.camera_buttons.append(Button(
            button_id="other:buttons:shock",
            target=shock,
        ))

    def run(self):
        global CAMERA
        global FOOD
        global VIEWPORT
        while True:
            self.clock.tick(self.fps)
            self.draw()
            self.tick()

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    sys.exit()

                if event.type == pg.KEYUP:
                    if event.key == pg.K_SPACE:
                        if CAMERA:
                            self.on_camera_down()
                        else:
                            if POWER > 0:
                                CAMERA = True

                    if event.key == pg.K_ESCAPE:
                        pg.event.set_grab(False)

                if event.type == pg.MOUSEBUTTONUP:
                    pg.event.set_grab(True)

                    if CAMERA:
                        for button in self.camera_buttons:
                            button.get_presssed()
                        for button in self.current_camera.buttons:
                            button.get_presssed()
                    else:
                        for button in self.room_buttons:
                            button.get_presssed()

            mx, my = pg.mouse.get_pos()
            x, y, w, h = VIEWPORT
            if mx - 30 <= 0 and x >= -375:
                x -= 30
            if mx + 30 >= WINDOW_SIZE[0] and x <= 375:
                x += 30

            VIEWPORT = (x, y, w, h)

    def on_camera_down(self):
        global CAMERA
        CAMERA = False
        if JUMPSCARE_QUEUE.qsize() != 0:
            self.draw()
            enemy = JUMPSCARE_QUEUE.get()
            enemy.jumpscare(self.window)

    def draw(self):
        self.window.fill(pg.Color(0, 0, 0))
        if CAMERA:
            self.current_camera.draw(self.window)
            for enemy in self.enemies:
                if self.current_camera.name == enemy.current_room:
                    enemy.draw(self.window)
            cameras_sprite = pg.image.load("resources/other/cameras.png").convert_alpha()

            darken_surface = pg.Surface(WINDOW_SIZE, pg.SRCALPHA)
            darken_surface.fill(pg.Color(0, 0, 0, 200))
            self.window.blit(darken_surface, (0, 0))

            self.window.blit(cameras_sprite, (900, 400))
            for camera_button in self.camera_buttons:
                camera_button.draw(self.window)
            for enemy in self.enemies:
                if enemy.id == "enemies:bat" and enemy.current_room == self.current_camera.name:
                    food_text = self.font.render(f"Food: {FOOD}", True, pg.Color(0, 0, 0))
                    self.window.blit(food_text, (1000, 0))
            for room in self.rooms:
                if room == self.current_camera and len(room.buttons) > 0:
                    for button in room.buttons:
                        button.draw(self.window)
        else:
            self.window.blit(self.main_room_sprite, get_actual_pos((0, 0), VIEWPORT))
            for button in self.room_buttons:
                button.draw(self.window)
            for enemy in self.enemies:
                if enemy.current_room in DOORS.keys():
                    enemy.draw(self.window, relative=True)
            for enemy in self.enemies:
                if enemy.id == "enemies:rat" and enemy.state == 1:
                    color = pg.Color(255, 0, 0)
                else:
                    color = pg.Color(0, 0, 0)
            power_text = self.font.render(f"Power: {int(POWER)}%", True, color)
            self.window.blit(power_text, get_actual_pos((0, 0), VIEWPORT))

            seconds_left = int((self.minutes * 60) - (time.time() - START_TIME))
            if seconds_left%60 >= 10:
                time_string = f"{seconds_left // 60}:{seconds_left % 60}"
            else:
                time_string = f"{seconds_left // 60}:0{seconds_left % 60}"

            time_text = self.font.render(f"Time Left: {time_string}", True, pg.Color(0, 0, 0))
            self.window.blit(time_text, get_actual_pos((900, 0), VIEWPORT))

        if POWER <= 0:
            darken_surface = pg.Surface(WINDOW_SIZE, pg.SRCALPHA)
            darken_surface.fill(pg.Color(0, 0, 0, 220))
            self.window.blit(darken_surface, (0, 0))
        pg.display.update()

    def tick(self):
        global POWER
        global CAMERA
        for enemy in self.enemies:
            enemy.tick()

        if CAMERA:
            POWER -= 0.0035 * self.power_mult
        for door in list(DOORS.keys()):
            if DOORS[door]:
                POWER -= 0.0035 * self.power_mult
        POWER -= 0.0035 * self.power_mult

        if POWER <= 0:
            for door in list(DOORS.keys()):
                DOORS[door] = False
            CAMERA = False

        if (time.time() - START_TIME) % (4 * 60) < 0.05:
            for enemy in self.enemies:
                enemy.difficulty += 5
                if enemy.difficulty > 20:
                    enemy.difficulty = 20

        if time.time() - START_TIME > self.minutes * 60:
            with open("data/data.json", "w+") as file:
                data = json.load(file)
                data[self.level] = True
                json.dump(data, file)
            sys.exit()


if __name__ == '__main__':
    START_TIME = time.time()
    CAMERA = False
    POWER = 100
    MAX_FOOD = 100
    FOOD = MAX_FOOD
    WINDOW_SIZE = (1280, 720)
    JUMPSCARE_QUEUE = queue.Queue()
    # lower is harder for MASTER_DIFFICULTY
    MASTER_DIFFICULTY = 275
    OFFICE_ROOM = "1e"
    VIEWPORT = (0, 0, 1280, 720)
    DOORS = {"1d": False, "2d": False}
    level = input("LEVEL: ")
    level = f"levels:{level}"
    game = Game(level)
    game.run()
