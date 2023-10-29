import random
import sys

import pygame
from pygame.locals import *

from classes.Animation import Animation
from classes.Camera import Camera
from classes.Collider import Collider
from classes.EntityCollider import EntityCollider
from classes.Input import Input
from classes.Pause import Pause
from classes.Sprites import Sprites
from entities.EntityBase import EntityBase
from entities.Mushroom import RedMushroom
from traits.bounce import bounceTrait
from traits.go import GoTrait
from traits.jump import JumpTrait

spriteCollection = Sprites().spriteCollection
smallAnimation = Animation(
    [
        spriteCollection["mario_run1"].image,
        spriteCollection["mario_run2"].image,
        spriteCollection["mario_run3"].image,
    ],
    spriteCollection["mario_idle"].image,
    spriteCollection["mario_jump"].image,
)
bigAnimation = Animation(
    [
        spriteCollection["mario_big_run1"].image,
        spriteCollection["mario_big_run2"].image,
        spriteCollection["mario_big_run3"].image,
    ],
    spriteCollection["mario_big_idle"].image,
    spriteCollection["mario_big_jump"].image,
)


class Mario(EntityBase):
    def __init__(self, x, y, level, screen, dashboard, sound, gravity=0.8):
        super(Mario, self).__init__(x, y, gravity)
        self.camera = Camera(self.rect, self)
        self.sound = sound
        self.input = Input(self)
        self.inAir = False
        self.inJump = False
        self.powerUpState = 0
        self.invincibilityFrames = 0
        self.checkInv = False
        self.traits = {
            "jumpTrait": JumpTrait(self),
            "goTrait": GoTrait(smallAnimation, screen, self.camera, self),
            "bounceTrait": bounceTrait(self),
        }

        self.levelObj = level
        self.collision = Collider(self, level)
        self.screen = screen
        self.EntityCollider = EntityCollider(self)
        self.dashboard = dashboard
        self.restart = False
        self.pause = False
        self.pauseObj = Pause(screen, self, dashboard)
        self.oldList = []

    def update(self):
        if self.checkInv is False:
            if self.invincibilityFrames > 0:
                self.invincibilityFrames -= 1
        self.updateTraits()
        self.moveMario()
        self.camera.move()
        self.applyGravity()
        self.checkEntityCollision()
        self.input.checkForInput()

    def moveMario(self):
        self.rect.y += self.vel.y
        self.collision.checkY()
        self.rect.x += self.vel.x
        self.collision.checkX()

    def checkEntityCollision(self):
        for ent in self.levelObj.entityList:
            collisionState = self.EntityCollider.check(ent)
            if collisionState.isColliding:
                if ent.type == "Item":
                    self._onCollisionWithItem(ent)
                elif ent.type == "Block":
                    self._onCollisionWithBlock(ent)
                elif ent.type == "Blocks":
                    self._onCollisionWithBlocks(ent)
                elif ent.type == "Mob":
                    self._onCollisionWithMob(ent, collisionState)
                elif ent.type == "ItemVIP":
                    self._onCollisionWithItemVIP(ent)

    def _onCollisionWithBlocks(self, block):
        if not block.triggered:
            self.dashboard.coins += 1
            self.sound.play_sfx(self.sound.bump)
        else:
            if block.rect.x < self.rect.x:
                self.levelObj.addCoinBrick(
                    int(self.rect.x / 32 + 2), int(self.rect.y / 32 - 3)
                )
            else:
                self.levelObj.addCoinBrick(
                    int(self.rect.x / 32 - 2), int(self.rect.y / 32 - 3)
                )

        block.triggered = True

    def _onCollisionWithItem(self, item):
        self.levelObj.entityList.remove(item)
        self.dashboard.points += 100
        self.dashboard.coins += 1
        self.sound.play_sfx(self.sound.coin)

    def _onCollisionWithItemVIP(self, item):
        self.levelObj.entityList.remove(item)
        self.dashboard.points += 1000
        self.sound.play_sfx(self.sound.coin)
        self.checkInv = True
        self.invincibilityFrames += 10000000

    def _onCollisionWithBlock(self, block):
        if not block.triggered:
            self.dashboard.coins += 1
            self.sound.play_sfx(self.sound.bump)
        block.triggered = True

    def _onCollisionWithMob(self, mob, collisionState):
        if self.checkInv is True:
            if isinstance(mob, RedMushroom) and mob.alive:
                self.powerup(1)
                self.killEntity(mob)
                self.sound.play_sfx(self.sound.powerup)
            elif (
                collisionState.isColliding
                and mob.alive
                and not mob.active
                and not mob.bouncing
            ):
                self.bounce()
                mob.bouncing = True
                if mob.rect.x < self.rect.x:
                    mob.leftrightTrait.direction = -1
                    mob.rect.x += -5
                    self.sound.play_sfx(self.sound.kick)
                else:
                    mob.rect.x += 5
                    mob.leftrightTrait.direction = 1
                    self.sound.play_sfx(self.sound.kick)
            else:
                self.killEntity(mob)
                self.sound.play_sfx(self.sound.stomp)
        else:
            if isinstance(mob, RedMushroom) and mob.alive:
                self.powerup(1)
                self.killEntity(mob)
                self.sound.play_sfx(self.sound.powerup)
            elif collisionState.isTop and (mob.alive or mob.bouncing):
                self.sound.play_sfx(self.sound.stomp)
                self.rect.bottom = mob.rect.top
                self.bounce()
                self.killEntity(mob)
            elif collisionState.isTop and mob.alive and not mob.active:
                self.sound.play_sfx(self.sound.stomp)
                self.rect.bottom = mob.rect.top
                mob.timer = 0
                self.bounce()
                mob.alive = False
            elif (
                collisionState.isColliding
                and mob.alive
                and not mob.active
                and not mob.bouncing
            ):
                mob.bouncing = True
                if mob.rect.x < self.rect.x:
                    mob.leftrightTrait.direction = -1
                    mob.rect.x += -5
                    self.sound.play_sfx(self.sound.kick)
                else:
                    mob.rect.x += 5
                    mob.leftrightTrait.direction = 1
                    self.sound.play_sfx(self.sound.kick)
            elif (
                collisionState.isColliding
                and mob.alive
                and not self.invincibilityFrames
            ):
                if self.powerUpState == 0:
                    self.gameOver()
                elif self.powerUpState == 1:
                    self.powerUpState = 0
                    self.traits["goTrait"].updateAnimation(smallAnimation)
                    x, y = self.rect.x, self.rect.y
                    self.rect = pygame.Rect(x, y + 32, 32, 32)
                    self.invincibilityFrames = 60
                    self.sound.play_sfx(self.sound.pipe)

    def bounce(self):
        self.traits["bounceTrait"].jump = True

    def killEntity(self, ent):
        if ent.__class__.__name__ != "Koopa":
            ent.alive = False
        else:
            ent.timer = 0
            ent.leftrightTrait.speed = 1
            ent.alive = True
            ent.active = False
            ent.bouncing = False
        self.dashboard.points += 100

    def gameOver(self):
        srf = pygame.Surface((640, 480))
        srf.set_colorkey((255, 255, 255), pygame.RLEACCEL)
        srf.set_alpha(128)
        self.sound.music_channel.stop()
        self.sound.music_channel.play(self.sound.death)

        for i in range(500, 20, -2):
            srf.fill((0, 0, 0))
            pygame.draw.circle(
                srf,
                (255, 255, 255),
                (int(self.camera.x + self.rect.x) + 16, self.rect.y + 16),
                i,
            )
            self.screen.blit(srf, (0, 0))
            pygame.display.update()
            self.input.checkForInput()
        while self.sound.music_channel.get_busy():
            pygame.display.update()
            self.input.checkForInput()

        self.restart = True

    # --------------------------------------------------------------------------
    def gameBoss(self):
        isWin = False

        class Dragon:
            def __init__(self, window_width, window_height):
                self.image = self.load_image("./img/princess.png")
                self.imagerect = self.image.get_rect()
                self.imagerect.right = window_width
                self.imagerect.top = window_height / 2
                self.up = False
                self.down = True
                self.velocity = 15

            def update(self, cactusrect, firerect, Canvas):
                if self.imagerect.top < cactusrect.bottom:
                    self.up = False
                    self.down = True

                if self.imagerect.bottom > firerect.top:
                    self.up = True
                    self.down = False

                if self.down:
                    self.imagerect.bottom += self.velocity

                if self.up:
                    self.imagerect.top -= self.velocity

                Canvas.blit(self.image, self.imagerect)

            def return_height(self):
                h = self.imagerect.top
                return h

            def load_image(self, imagename):
                return pygame.image.load(imagename)

        class Flames:
            flamespeed = 13

            def __init__(self, window_width, window_height, Dragon):
                self.image = self.load_image("./img/fireball.png")
                self.imagerect = self.image.get_rect()
                self.height = Dragon.return_height() + 20
                self.surface = pygame.transform.scale(self.image, (20, 20))
                self.imagerect = pygame.Rect(window_width - 106, self.height, 20, 20)

            def update(self):
                self.imagerect.left -= self.flamespeed / 3
                self.imagerect.top += random.randint(-15, 15)

            def collision(self):
                if self.imagerect.left == 0:
                    return True
                else:
                    return False

            def load_image(self, imagename):
                return pygame.image.load(imagename)

        class Maryo:
            speed = 10
            downspeed = 20

            def __init__(self, window_height):
                self.window_height = window_height
                self.image = self.load_image("./img/maryo.png")
                self.imagerect = self.image.get_rect()
                self.imagerect.topleft = (50, window_height / 2)
                self.score = 0

            def update(
                self,
                moveup,
                movedown,
                moveleft,
                moveright,
                gravity,
                cactusrect,
                firerect,
            ):
                if moveleft:
                    self.imagerect.left -= self.speed

                if moveright:
                    self.imagerect.right += self.speed

                if moveup and (self.imagerect.top > cactusrect.bottom):
                    self.imagerect.top -= self.speed

                if movedown and (self.imagerect.bottom < firerect.top):
                    self.imagerect.bottom += self.downspeed

                if gravity and (self.imagerect.bottom < firerect.top):
                    self.imagerect.bottom += self.speed / 3

            def load_image(self, imagename):
                return pygame.image.load(imagename)

        class Game:
            def __init__(self, screen):
                self.window_height = 480
                self.window_width = 640
                self.blue = (0, 0, 255)
                self.black = (0, 0, 0)
                self.white = (255, 255, 255)
                self.fps = 25
                self.level = 0
                self.addnewflamerate = 20

                self.mainClock = pygame.time.Clock()
                # self.Canvas = pygame.display.set_mode((self.window_width, self.window_height))
                self.Canvas = screen
                self.font = pygame.font.SysFont(None, 48)
                self.scorefont = pygame.font.SysFont(None, 30)

                self.fireimage = pygame.image.load("./img/fire_bricks.png")
                self.firerect = self.fireimage.get_rect()

                self.Canvas.blit(self.fireimage, self.firerect)
                self.cactusimage = pygame.image.load("./img/cactus_bricks.png")
                self.cactusrect = self.cactusimage.get_rect()

                self.startimage = pygame.image.load("./img/start.png")
                self.startimagerect = self.startimage.get_rect()
                self.startimagerect.centerx = self.window_width / 2
                self.startimagerect.centery = self.window_height / 2

                self.endimage = pygame.image.load("./img/end1.gif")
                self.endimagerect = self.endimage.get_rect()
                self.endimagerect.centerx = 4 * self.window_width / 5
                self.endimagerect.centery = 2 * self.window_height / 4

                self.loseimage = pygame.image.load("./img/lose.jpg")
                self.loseimagerect = self.loseimage.get_rect()
                self.loseimagerect.centerx = self.window_width / 2
                self.loseimagerect.centery = self.window_height / 2

            def terminate(self):  # to end the program
                pygame.quit()
                sys.exit()

            def wait_for_key(self):
                while True:  # to wait for user to start
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            self.terminate()
                        if (
                            event.type == pygame.KEYDOWN
                        ):  # to terminate if the user presses the escape key
                            if event.key == pygame.K_ESCAPE:
                                self.terminate()
                            return

            def flamehitsmario(
                self, playerrect, flame_list
            ):  # to check if flame has hit mario or not
                for f in flame_list:
                    if playerrect.colliderect(f.imagerect):
                        return True
                return False

            def dragonhitsmario(self, playerrect, dragon):
                if playerrect.colliderect(dragon):
                    return True
                return False

            def draw_text(
                self, text, font, surface, x, y
            ):  # to display text on the screen
                textobj = font.render(text, 1, self.white)
                textrect = textobj.get_rect()
                textrect.topleft = (x, y)
                surface.blit(textobj, textrect)

            def check_level(self, score):
                if score in range(0, 250):
                    self.firerect.top = self.window_height - 50
                    self.cactusrect.bottom = 50
                    self.level = 1
                elif score in range(250, 500):
                    self.firerect.top = self.window_height - 100
                    self.cactusrect.bottom = 100
                    self.level = 2
                elif score in range(500, 750):
                    self.level = 3
                    self.firerect.top = self.window_height - 150
                    self.cactusrect.bottom = 150
                elif score in range(750, 1000):
                    self.level = 4
                    self.firerect.top = self.window_height - 200
                    self.cactusrect.bottom = 200

            def load_image(imagename):
                return pygame.image.load(imagename)

            def main_menu(self):
                self.Canvas.fill(self.black)

                pygame.display.update()
                self.mainClock.tick(self.fps)

                while True:
                    self.run_game()
                    self.wait_for_key()
                    break

            def run_game(self):
                flame_list = []

                moveup = movedown = moveleft = moveright = gravity = False
                flameaddcounter = 0
                maryo = Maryo(self.window_height)
                dragon = Dragon(self.window_width, self.window_height)

                while True:
                    self.Canvas.fill(self.black)
                    for event in pygame.event.get():
                        if event.type == QUIT:
                            self.terminate()

                        if event.type == KEYDOWN:
                            if event.key == K_LEFT:
                                movedown = False
                                moveup = False
                                gravity = False
                                moveleft = True
                                moveright = False

                            if event.key == K_RIGHT:
                                movedown = False
                                moveup = False
                                gravity = False
                                moveleft = False
                                moveright = True

                            if event.key == K_UP:
                                movedown = False
                                moveup = True
                                gravity = False
                                moveleft = False
                                moveright = False

                            if event.key == K_DOWN:
                                moveup = False
                                movedown = True
                                gravity = False
                                moveleft = False
                                moveright = False

                        if event.type == KEYUP:
                            if event.key == K_ESCAPE:
                                self.terminate()

                            if event.key == K_UP:
                                moveup = False
                                gravity = True

                            if event.key == K_DOWN:
                                movedown = False
                                gravity = True

                            if event.key == K_LEFT:
                                moveleft = False
                                gravity = True

                            if event.key == K_RIGHT:
                                moveright = False
                                gravity = True

                    flameaddcounter += 1
                    self.check_level(maryo.score)

                    if flameaddcounter == self.addnewflamerate:
                        flameaddcounter = 0
                        newflame = Flames(self.window_width, self.window_height, dragon)
                        flame_list.append(newflame)

                    for f in flame_list:
                        Flames.update(f)
                    for f in flame_list:
                        if f.imagerect.left <= 0:
                            flame_list.remove(f)

                    maryo.update(
                        moveup,
                        movedown,
                        moveleft,
                        moveright,
                        gravity,
                        self.cactusrect,
                        self.firerect,
                    )
                    dragon.update(self.cactusrect, self.firerect, self.Canvas)

                    # self.Canvas.fill(self.black)
                    self.Canvas.blit(self.cactusimage, self.cactusrect)
                    self.Canvas.blit(self.fireimage, self.firerect)
                    self.Canvas.blit(maryo.image, maryo.imagerect)
                    self.Canvas.blit(dragon.image, dragon.imagerect)

                    for f in flame_list:
                        self.Canvas.blit(f.surface, f.imagerect)

                    if self.dragonhitsmario(maryo.imagerect, dragon.imagerect):
                        isWin = True
                        break

                    if self.flamehitsmario(maryo.imagerect, flame_list):
                        isWin = False
                        break

                    if (maryo.imagerect.top <= self.cactusrect.bottom) or (
                        maryo.imagerect.bottom >= self.firerect.top
                    ):
                        isWin = False
                        break

                    pygame.display.update()
                    self.mainClock.tick(self.fps)

                if isWin is True:
                    self.Canvas.blit(self.endimage, self.endimagerect)
                    pygame.display.update()
                    self.wait_for_key()
                else:
                    self.Canvas.blit(self.loseimage, self.loseimagerect)
                    pygame.display.update()
                    self.wait_for_key()

        game = Game(self.screen)
        game.main_menu()
        self.restart = True

    # --------------------------------------------------------------------------
    def getPos(self):
        return self.camera.x + self.rect.x, self.rect.y

    def setPos(self, x, y):
        self.rect.x = x
        self.rect.y = y

    def powerup(self, powerupID):
        if self.powerUpState == 0:
            if powerupID == 1:
                self.powerUpState = 1
                self.traits["goTrait"].updateAnimation(bigAnimation)
                self.rect = pygame.Rect(self.rect.x, self.rect.y - 32, 32, 64)
                self.invincibilityFrames = 20
