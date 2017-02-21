import cozmo
import asyncio
from Common.woc import WOC
import pygame
import random
import sys
from cozmo.util import degrees, distance_mm, speed_mmps
from math import atan2,pi, sqrt

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SCREEN_WIDTH = 800;
SCREEN_HEIGHT = 600;


class Block(pygame.sprite.Sprite):
    # This class represents a car. It derives from the "Sprite" class in Pygame.

    def __init__(self):
        # Call the parent class (Sprite) constructor
        super().__init__()

        # Pass in the color of the car, and its x and y position, width and height.
        # Set the background color and set it to be transparent
        self.image = pygame.Surface([50, 50])
        self.image.fill(BLACK)
        # self.image.set_colorkey(BLACK)

        # Instead we could load a proper pciture of a car...
        self.image = pygame.image.load("Images/11.jpg").convert_alpha()

        # Fetch the rectangle object that has the dimensions of the image.
        self.rect = self.image.get_rect()

    def update(self):
        pos = pygame.mouse.get_pos()
        self.rect.x = pos[0]
        self.rect.y = pos[1]

class CozmoController(WOC):

    def __init__(self, *a, **kw):
        WOC.__init__(self)

        cozmo.setup_basic_logging()
        try:
            cozmo.connect(self.run)
        except cozmo.ConnectionError as e:
            sys.exit("A connection error occurred: %s" % e)

    async def run(self, coz_conn):
        asyncio.set_event_loop(coz_conn._loop)
        self.coz = await coz_conn.wait_for_robot()

        self.exit_flag = False

        await self.getPath()
        await self.moveCozmo();

    async def moveCozmo(self):
        print(self.steps);
        for step in self.steps:
            if step[0] == 'rotate':
                await self.coz.turn_in_place(degrees(step[1])).wait_for_completed()
            if step[0] == 'move':
                await self.coz.drive_straight(distance_mm(abs(step[1])), speed_mmps(50)).wait_for_completed()
            if step[0] == 'action':
                await self.coz.set_lift_height(1.0).wait_for_completed();
                await self.coz.set_lift_height(0.0).wait_for_completed();

    async def getPath(self):
        clock = pygame.time.Clock()

        (width, height) = (SCREEN_WIDTH, SCREEN_HEIGHT)
        screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption('Cozmo Controller')
        background_colour = (255, 255, 255)
        screen.fill(background_colour)

        fpsClock = pygame.time.Clock()

        all_lines = [];

        self.steps = [];
        currentMovement = 0;  # 0 is start, 1 is vertical and 2 is horizontal
        startPosition = (0, 0);
        draw = False
        finished_drawing = False
        prevX, prevY = 0, 0
        while not finished_drawing:
            for event in pygame.event.get():
                if (event.type == pygame.KEYUP):
                    if (event.key == pygame.K_d):
                        finished_drawing = True;
                if event.type == pygame.MOUSEBUTTONDOWN:
                    draw = True
                    (actualX, actualY) = pygame.mouse.get_pos()
                    if prevX != 0 and prevY != 0:
                        screen.fill(WHITE);
                        if len(all_lines) > 1:
                            pygame.draw.lines(screen, (0, 0, 0), False, all_lines, 5)
                        pygame.draw.line(screen, (0, 0, 0), (prevX, prevY), (actualX, actualY), 5)
                        pygame.display.flip()
                if event.type == pygame.MOUSEMOTION and draw == True:
                    (actualX, actualY) = pygame.mouse.get_pos()
                    if prevX != 0 and prevY != 0:
                        screen.fill(WHITE);
                        if len(all_lines) > 1:
                            pygame.draw.lines(screen, (0, 0, 0), False, all_lines, 5)
                        pygame.draw.line(screen, (0, 0, 0), (prevX, prevY), (actualX, actualY), 5)
                        pygame.display.flip()
                    else:
                        startPosition = (actualX, actualY);
                        prevX, prevY = actualX, actualY
                        all_lines.append((prevX, prevY));

                if event.type == pygame.MOUSEBUTTONUP:
                    (actualX, actualY) = pygame.mouse.get_pos()
                    prevX, prevY = actualX, actualY
                    all_lines.append((prevX, prevY));
                    draw = False

        prevPoint = (0, 0);
        prevRotation = 0;
        for point in all_lines:
            if (prevPoint[0] == 0 and prevPoint[1] == 0):
                prevPoint = point;
            else:
                delta_x = point[0] - prevPoint[0]
                delta_y = point[1] - prevPoint[1]
                angle = -atan2(delta_y, delta_x) * 180 / pi
                dist = sqrt(delta_x * delta_x + delta_y * delta_y);
                angle -= 90;
                rotate_angle = angle - prevRotation;
                if rotate_angle >= 180:
                    rotate_angle = 180 - rotate_angle;
                if rotate_angle <= -180:
                    rotate_angle = -180 - rotate_angle;
                self.steps.append(("rotate", rotate_angle));
                self.steps.append(("move", dist));
                prevPoint = point;
                prevRotation = angle;

        all_blocks = pygame.sprite.Group()

        block = Block()
        block.rect.x = 10;
        block.rect.y = 10;

        all_blocks.add(block)

        all_blocks.draw(screen)
        pygame.display.flip()

        drag = False
        drag_list = [];
        found_action = False
        while not found_action:
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    drag = True
                    for box in all_blocks:
                        if box.rect.collidepoint(event.pos[0], event.pos[1]):
                            drag_list.append(box);
                if event.type == pygame.MOUSEBUTTONUP:
                    drag = False
                    drag_list = []
                    found_action = self.checkIntersection(all_blocks, all_lines);
                if event.type == pygame.MOUSEMOTION and drag == True:
                    screen.fill(WHITE)
                    pygame.draw.lines(screen, (0, 0, 0), False, all_lines, 5)
                    for block in drag_list:
                        block.update();
                    all_blocks.draw(screen)
                    pygame.display.flip()
                    clock.tick(60)
            pass;

    def checkIntersection(self, blocks,lines):
        intersection = (0,0);
        block = blocks.sprites()[0];
        prevPoint = (0,0);
        i=0;
        for point in lines:
            if(prevPoint[0] == 0 and prevPoint[1] == 0):
                prevPoint = point;
                i += 1;
                continue;
            all_points = self.get_line(prevPoint[0],prevPoint[1],point[0],point[1])
            for p in all_points:
                if block.rect.collidepoint(p[0], p[1]):
                    intersection = p;
                    break;
            if (intersection[0] != 0 and intersection[1] != 0):
                break;
            prevPoint = point;
            i += 1;

        if (intersection[0] != 0 and intersection[1] != 0):
            delta_x2 = lines[i][0] - intersection[0];
            delta_y2 = lines[i][1] - intersection[1];
            delta_x3 = lines[i - 1][0] - intersection[0];
            delta_y3 = lines[i - 1][1] - intersection[1];
            dist2 = sqrt(delta_x2 * delta_x2 + delta_y2 * delta_y2);
            dist3 = sqrt(delta_x3 * delta_x3 + delta_y3 * delta_y3);
            step_index = (i-1)*2 + 1;
            self.steps[step_index] = ("move", dist2);
            self.steps.insert(step_index,("action","arm"));
            self.steps.insert(step_index, ("move", dist3));
            return True;
        return False

    def get_line(self, x1, y1, x2, y2):
        points = []
        issteep = abs(y2 - y1) > abs(x2 - x1)
        if issteep:
            x1, y1 = y1, x1
            x2, y2 = y2, x2
        rev = False
        if x1 > x2:
            x1, x2 = x2, x1
            y1, y2 = y2, y1
            rev = True
        deltax = x2 - x1
        deltay = abs(y2 - y1)
        error = int(deltax / 2)
        y = y1
        ystep = None
        if y1 < y2:
            ystep = 1
        else:
            ystep = -1
        for x in range(x1, x2 + 1):
            if issteep:
                points.append((y, x))
            else:
                points.append((x, y))
            error -= deltay
            if error < 0:
                y += ystep
                error += deltax
        # Reverse the list if the coordinates were reversed
        if rev:
            points.reverse()
        return points
if __name__ == '__main__':
    CozmoController();