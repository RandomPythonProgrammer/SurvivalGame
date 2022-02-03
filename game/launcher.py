import json
import os
import sys
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame as pg
from main import Button


def get_current_level():
    with open("data/data.json", "r") as file:
        data = json.load(file)
        current_level = list(data.keys())[-1]
        for level in list(data.keys()):
            if data[level] == 0:
                current_level = level
                break
    return current_level


window_size = (1280, 720)
window = pg.display.set_mode(window_size)


def start_game():
    os.system(f"python main.py {get_current_level()}")
    sys.exit()


def reset():
    with open("data/data.json", "r") as file:
        data = json.load(file)
        for key in list(data.keys()):
            data[key] = 0
    with open("data/data.json", "w+") as file:
        json.dump(data, file)
    for button in buttons:
        if button.name == "play":
            button.text = f"Play (Level {get_current_level()})"


def how_to_play():
    os.system("notepad.exe HowToPlay.txt")


buttons = []

play_button = Button(
    text=f"Play (Level {get_current_level()})",
    location=(50, 75),
    size=(275, 100),
    boarder=3,
    font_size=48,
    text_location=(30, 30),
    target=start_game,
    name="play"
)

buttons.append(play_button)

reset_button = Button(
    text=f"Reset Progress",
    location=(50, 225),
    size=(275, 100),
    boarder=3,
    font_size=48,
    text_location=(20, 30),
    target=reset
)

buttons.append(reset_button)

how_top_lay_button = Button(
    text=f"How To Play",
    location=(50, 375),
    size=(275, 100),
    boarder=3,
    font_size=48,
    text_location=(40, 30),
    target=how_to_play
)

buttons.append(how_top_lay_button)


exit_button = Button(
    text=f"Exit",
    location=(50, 525),
    size=(275, 100),
    boarder=3,
    font_size=64,
    text_location=(90, 30),
    target=sys.exit
)

buttons.append(exit_button)

image = pg.image.load("resources/enemies/bat/bat0.png").convert_alpha()

pg.display.set_caption("Amazing Game")
pg.display.set_icon(pg.image.load("resources/enemies/dog/dog0.png").convert_alpha())

while True:
    for event in pg.event.get():
        if event.type == pg.QUIT:
            sys.exit()

        if event.type == pg.MOUSEBUTTONUP:
            for button in buttons:
                button.get_pressed()

    window.blit(image, (0, 100))

    for button in buttons:
        button.draw(window)

    pg.display.update()
