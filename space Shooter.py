import curses
import random
import time
import os
import json
import threading
import sys

try:
    from playsound import playsound
except ImportError:
    playsound = None

from typing import Optional
# Constants
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 24
PLAYER_CHAR = 'A'
ENEMY_CHAR = 'M'
BULLET_CHAR = '|'
ENEMY_BULLET_CHAR = '*'
POWERUP_CHAR = '+'
BOSS_CHAR = 'B'
MAX_BULLETS = 5
BOSS_HEALTH = 20
HIGHSCORE_FILE = 'highscores.json'

SOUND_SHOOT = 'shoot.wav'
SOUND_HIT = 'hit.wav'
SOUND_POWERUP = 'powerup.wav'
SOUND_GAMEOVER = 'gameover.wav'

class Bullet:
    def _init_(self, x, y, dy, char=BULLET_CHAR):
        self.x = SCREEN_WIDTH // 2  # which is 40
        self.y = SCREEN_HEIGHT - 2  # which is 22
        self.dy = dy
        self.char = char
        self.alive = True

    def update(self):
        self.y += self.dy
        if self.y < 1 or self.y >= SCREEN_HEIGHT:
            self.alive = False

    def draw(self, screen):
        if 0 < self.y < SCREEN_HEIGHT:
            try:
                screen.addch(self.y, self.x, self.char)
            except curses.error:
                pass

class Player:
    def _init_(self, x, y):
        self.x = x
        self.y = y
        self.lives = 3
        self.score = 0
        self.weapon_type = 1
        self.bullets = []

    def move(self, dx):
        self.x = max(1, min(SCREEN_WIDTH - 2, self.x + dx))

    def shoot(self):
        if len(self.bullets) < MAX_BULLETS:
            if self.weapon_type == 1:
                self.bullets.append(Bullet(self.x, self.y - 1, -1))
            elif self.weapon_type == 2:
                self.bullets.append(Bullet(self.x, self.y - 1, -1))
                self.bullets.append(Bullet(self.x - 1, self.y - 1, -1))
                self.bullets.append(Bullet(self.x + 1, self.y - 1, -1))
            elif self.weapon_type >= 3:
                for dx in [-2, -1, 0, 1, 2]:
                    self.bullets.append(Bullet(self.x + dx, self.y - 1, -1))

    def draw(self, screen):
        try:
            screen.addch(self.y, self.x, PLAYER_CHAR)
        except curses.error:
            pass

class Enemy:
    def _init_(self, x, y):
        self.x = x
        self.y = y
        self.alive = True
        self.fire_chance = 0.01

    def update(self):
        self.y += 1
        if self.y >= SCREEN_HEIGHT:
            self.alive = False

    def shoot(self):
        if random.random() < self.fire_chance:
            return Bullet(self.x, self.y + 1, 1, ENEMY_BULLET_CHAR)
        return None

    def draw(self, screen):
        if self.alive:
            try:
                screen.addch(self.y, self.x, ENEMY_CHAR)
            except curses.error:
                pass

class Boss:
    def _init_(self, x, y):
        self.x = x
        self.y = y
        self.health = BOSS_HEALTH
        self.alive = True
        self.direction = 1

    def update(self):
        self.x += self.direction
        if self.x <= 1 or self.x >= SCREEN_WIDTH - 2:
            self.direction *= -1

    def shoot(self):
        if random.random() < 0.1:
            return Bullet(self.x, self.y + 1, 1, ENEMY_BULLET_CHAR)
        return None

    def draw(self, screen):
        if self.alive:
            try:
                screen.addch(self.y, self.x, BOSS_CHAR)
            except curses.error:
                pass

class PowerUp:
    def _init_(self, x, y):
        self.x = x
        self.y = y
        self.alive = True

    def update(self):
        self.y += 1
        if self.y >= SCREEN_HEIGHT:
            self.alive = False

    def draw(self, screen):
        if self.alive:
            try:
                screen.addch(self.y, self.x, POWERUP_CHAR)
            except curses.error:
                pass

class HighScoreManager:
    def _init_(self, filename):
        self.filename = filename
        self.scores = self.load_scores()

    def load_scores(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                return json.load(f)
        return []

    def save_score(self, score):
        self.scores.append(score)
        self.scores = sorted(self.scores, reverse=True)[:10]
        with open(self.filename, 'w') as f:
            json.dump(self.scores, f)

    def display_scores(self, screen):
        screen.clear()
        screen.addstr(2, 10, "HIGH SCORES")
        for idx, score in enumerate(self.scores):
            screen.addstr(4 + idx, 10, f"{idx + 1}. {score}")
        screen.addstr(SCREEN_HEIGHT - 2, 2, "Press any key to return")
        screen.refresh()
        screen.getch()

def show_title(screen):
    title = [
        "   ___            __      __                ",
        "  / _ | ___  ___ / /____ / /  ___ ___ _  ___",
        " / __ |/ _ \\/ -) __/ -) _ \\/ _ `/  ' \\/ -_)",
        "// ||\\/\\/\\/\\/./\\,////\\_/ "
    ]
    screen.clear()
    for i, line in enumerate(title):
        screen.addstr(5 + i, 10, line)
    screen.addstr(15, 20, "Press any key to start")
    screen.refresh()
    screen.getch()

class Game:
    def _init_(self, screen):
        self.screen = screen
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 2)
        self.enemies = []
        self.enemy_bullets = []
        self.powerups = []
        self.boss: Optional[Boss] = None
        self.running = True
        self.paused = False
        self.highscores = HighScoreManager(HIGHSCORE_FILE)

    def spawn_enemy(self):
        x = random.randint(1, SCREEN_WIDTH - 2)
        self.enemies.append(Enemy(x, 1))

    def spawn_powerup(self):
        x = random.randint(1, SCREEN_WIDTH - 2)
        self.powerups.append(PowerUp(x, 1))

    def update(self):
        if random.random() < 0.05:
            self.spawn_enemy()
        if random.random() < 0.01:
            self.spawn_powerup()

        for e in self.enemies:
            e.update()
            shot = e.shoot()
            if shot:
                self.enemy_bullets.append(shot)

        if self.boss and self.boss.alive:
            self.boss.update()
            shot = self.boss.shoot()
            if shot:
                self.enemy_bullets.append(shot)

        for b in self.player.bullets:
            b.update()

        for eb in self.enemy_bullets:
            eb.update()

        for p in self.powerups:
            p.update()

        self.player.bullets = [b for b in self.player.bullets if b.alive]
        self.enemy_bullets = [b for b in self.enemy_bullets if b.alive]
        self.enemies = [e for e in self.enemies if e.alive]
        self.powerups = [p for p in self.powerups if p.alive]

        for bullet in self.player.bullets:
            for enemy in self.enemies:
                if enemy.alive and bullet.x == enemy.x and bullet.y == enemy.y:
                    enemy.alive = False
                    bullet.alive = False
                    self.player.score += 10
                    if playsound:
                        threading.Thread(target=playsound, args=(SOUND_HIT,), daemon=True).start()

        for eb in self.enemy_bullets:
            if eb.x == self.player.x and eb.y == self.player.y:
                eb.alive = False
                self.player.lives -= 1
                if self.player.lives <= 0:
                    self.running = False

        for p in self.powerups:
            if p.x == self.player.x and p.y == self.player.y:
                p.alive = False
                self.player.weapon_type = min(3, self.player.weapon_type + 1)
                if playsound:
                    threading.Thread(target=playsound, args=(SOUND_POWERUP,), daemon=True).start()

        if not self.enemies and not self.boss and random.random() < 0.02:
            self.boss = Boss(SCREEN_WIDTH // 2, 3)

        if self.boss:
            for bullet in self.player.bullets:
                if self.boss is not None and bullet.x == self.boss.x and bullet.y == self.boss.y:

                    bullet.alive = False
                    self.boss.health -= 1
                    if self.boss.health <= 0:
                        self.boss.alive = False
                        self.boss = None
                        self.player.score += 100

    def draw(self):
        self.screen.clear()
        self.player.draw(self.screen)
        for e in self.enemies:
            e.draw(self.screen)
        for b in self.player.bullets:
            b.draw(self.screen)
        for eb in self.enemy_bullets:
            eb.draw(self.screen)
        for p in self.powerups:
            p.draw(self.screen)
        if self.boss and self.boss.alive:
            self.boss.draw(self.screen)
        self.screen.addstr(0, 2, f"Score: {self.player.score}  Lives: {self.player.lives}")
        if self.paused:
            self.screen.addstr(SCREEN_HEIGHT // 2, SCREEN_WIDTH // 2 - 5, "[PAUSED]")
        self.screen.refresh()

    def run(self):
        self.screen.nodelay(True)
        while self.running:
            try:
                key = self.screen.getch()
                if key == ord('a'):
                    self.player.move(-1)
                elif key == ord('d'):
                    self.player.move(1)
                elif key == ord('w'):
                    self.player.shoot()
                    if playsound:
                        threading.Thread(target=playsound, args=(SOUND_SHOOT,), daemon=True).start()
                elif key == ord('p'):
                    self.paused = not self.paused
                elif key == ord('q'):
                    self.running = False
            except:
                pass

            if not self.paused:
                self.update()
                self.draw()
            time.sleep(0.05)

        self.end_game()

    def end_game(self):
        if playsound:
            threading.Thread(target=playsound, args=(SOUND_GAMEOVER,), daemon=True).start()
        self.highscores.save_score(self.player.score)
        self.highscores.display_scores(self.screen)

def main(screen):
    curses.curs_set(0)
    def main(screen):
        curses.curs_set(0)
        global SCREEN_WIDTH, SCREEN_HEIGHT
        SCREEN_HEIGHT, SCREEN_WIDTH = screen.getmaxyx()

    show_title(screen)
    while True:
        game = Game(screen)
        game.run()
        screen.addstr(SCREEN_HEIGHT // 2, SCREEN_WIDTH // 2 - 6, "Play Again? (y/n)")
        screen.refresh()
        key = screen.getch()
        if key != ord('y'):
            break

if _name_ == '_main_':
    curses.wrapper(main)

