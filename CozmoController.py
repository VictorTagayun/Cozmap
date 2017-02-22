import cozmo
import asyncio
from Common.woc import WOC
import pygame
import random
import sys
from cozmo.util import degrees, distance_mm, speed_mmps
from math import atan2,pi, sqrt
from textbox import TextBox

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SCREEN_WIDTH = 800;
SCREEN_HEIGHT = 600;

COMMAND_MOVE = 'move'
COMMAND_ROTATE = 'rotate'
COMMAND_ACTION = 'action'
KEY_REPEAT_SETTING = (200,70)

LEFT_MARGIN = 75;
TOP_MARGIN = 40;

class Block(pygame.sprite.Sprite):

    action = ""
    variable = ""
    action_id = -1
    panel_block = True
    intersection_point = (-1,-1)

    def __init__(self, _panel_block = True, _action = "arm", _variable=""):
        super().__init__()

        if(_variable == None):
            _variable = "";
        self.panel_block = _panel_block
        self.action_id = -1
        self.intersection_point = (-1,-1)
        self.action = _action
        self.variable = _variable

        self.image = pygame.Surface([50, 50])

        self.image.fill(BLACK)

        self.image = pygame.image.load("Images/" + self.action + ".jpg").convert_alpha()

        self.rect = self.image.get_rect()

        if not self.panel_block:
            font = pygame.font.Font(None, 12)
            self.text = font.render(str(_variable), True, (0, 0, 128))
            W = self.text.get_width()
            H = self.text.get_height()
            self.image.blit(self.text, (0, 0))

    def update(self):
        self.image.blit(self.text, (50, 50))
        pos = pygame.mouse.get_pos()
        self.rect.x = pos[0]
        self.rect.y = pos[1]

class CozmoController(WOC):

    action_var = {};
    cur_instruction = "";

    run_button = None
    restart_button = None

    def __init__(self, *a, **kw):
        WOC.__init__(self)

        cozmo.setup_basic_logging()
        try:
            cozmo.connect(self.run)
        except cozmo.ConnectionError as e:
            print("A connection error occurred: %s" % e)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.run())

    async def run(self, coz_conn=None):
        if coz_conn != None:
            asyncio.set_event_loop(coz_conn._loop)
            self.coz = await coz_conn.wait_for_robot()

        self.exit_flag = False

        ret = False
        while ret == False:
            ret = await self.getPath()

        await self.moveCozmo();

    async def moveCozmo(self):
        print(self.steps);
        for step in self.steps:
            if step[0] == COMMAND_ROTATE:
                await self.coz.turn_in_place(degrees(step[1])).wait_for_completed()
            elif step[0] == COMMAND_MOVE:
                await self.coz.drive_straight(distance_mm(abs(step[1])), speed_mmps(50)).wait_for_completed()
            elif step[0] == COMMAND_ACTION:
                if(step[1][1] == "arm"):
                    lift_to = 1.0;
                    if (step[1][2] != ""):
                        try:
                            lift_to = float(step[1][2])
                        except:
                            lift_to = 1.0
                    await self.coz.set_lift_height(lift_to).wait_for_completed();
                    await self.coz.set_lift_height(0.0).wait_for_completed();
                elif(step[1][1] == "face"):
                    lift_to = 1.0;
                    if (step[1][2] != ""):
                        try:
                            lift_to = float(step[1][2])
                        except:
                            lift_to = 1.0
                    await self.coz.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE*lift_to).wait_for_completed()
                    await self.coz.set_head_angle(cozmo.robot.MIN_HEAD_ANGLE).wait_for_completed()
                elif (step[1][1] == "say"):
                    say = "Hello there";
                    if(step[1][2] != ""):
                        say = step[1][2]
                    await self.coz.say_text(say, duration_scalar=1, voice_pitch=-1).wait_for_completed()

    async def makeScreen(self, screen, show_buttons = True):
        background_colour = (255, 255, 255)
        screen.fill(background_colour)
        pygame.draw.line(screen, (128, 128, 128), (LEFT_MARGIN,0),(LEFT_MARGIN,SCREEN_HEIGHT), 2)
        pygame.draw.line(screen, (128, 128, 128), (0, TOP_MARGIN), (SCREEN_WIDTH, TOP_MARGIN), 2)
        pygame.draw.line(screen, (128, 128, 128), (0, SCREEN_HEIGHT-TOP_MARGIN), (SCREEN_WIDTH, SCREEN_HEIGHT-TOP_MARGIN), 2)
        font = pygame.font.Font(None, 36)
        text = font.render(str("COZMAP"), True, (128, 128, 128))
        W = text.get_width()
        screen.blit(text, (LEFT_MARGIN + ((SCREEN_WIDTH-LEFT_MARGIN)-W)/2, 8));

        font2 = pygame.font.Font(None, 24)
        instruction_text = font2.render(self.cur_instruction, True, (128, 128, 128))
        W2 = instruction_text.get_width()
        H2 = instruction_text.get_height()
        screen.blit(instruction_text, (LEFT_MARGIN + ((SCREEN_WIDTH-LEFT_MARGIN) - W2) / 2, SCREEN_HEIGHT-H2-8));

        self.restart_button = pygame.Rect((8, SCREEN_HEIGHT - TOP_MARGIN + 8, LEFT_MARGIN-16, TOP_MARGIN - 16))
        pygame.draw.rect(screen, (128, 0, 0), self.restart_button)
        screen.blit(font2.render("Clear", True, (255, 255, 255)), (self.restart_button[0] + 8, self.restart_button[1] + 5))

        if show_buttons:
            self.run_button = pygame.Rect((SCREEN_WIDTH-56, SCREEN_HEIGHT-TOP_MARGIN+8, 48, TOP_MARGIN-16))
            pygame.draw.rect(screen, (0,128,0), self.run_button)
            screen.blit(font2.render("Run",True,(255,255,255)),(self.run_button[0]+8,self.run_button[1]+5))

    async def getPath(self):
        clock = pygame.time.Clock()

        (width, height) = (SCREEN_WIDTH, SCREEN_HEIGHT)
        screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption('Cozmap')
        pygame.key.set_repeat(*KEY_REPEAT_SETTING)
        self.cur_instruction = "Draw paths by clicking and dragging the mouse. Press 'D' when you are done"
        await self.makeScreen(screen, False);
        pygame.display.flip()

        all_lines = [];

        self.steps = [];
        currentMovement = 0;  # 0 is start, 1 is vertical and 2 is horizontal
        draw = False
        finished_drawing = False
        prevX, prevY = 0, 0
        while not finished_drawing:
            for event in pygame.event.get():
                if (event.type == pygame.KEYUP):
                    if (event.key == pygame.K_d):
                        finished_drawing = True;
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if (self.restart_button != None and self.restart_button.collidepoint(event.pos[0],event.pos[1])):
                        return False;
                    draw = True
                    (actualX, actualY) = pygame.mouse.get_pos()
                    if (actualX < LEFT_MARGIN):
                        actualX = LEFT_MARGIN;
                    if (actualY < TOP_MARGIN):
                        actualY = TOP_MARGIN;
                    if (actualY > SCREEN_HEIGHT - TOP_MARGIN):
                        actualY = SCREEN_HEIGHT - TOP_MARGIN;
                    if prevX != 0 and prevY != 0:
                        await self.makeScreen(screen, False);
                        if len(all_lines) > 1:
                            pygame.draw.lines(screen, (0, 0, 0), False, all_lines, 5)
                        pygame.draw.line(screen, (0, 0, 0), (prevX, prevY), (actualX, actualY), 5)
                        pygame.display.flip()
                if event.type == pygame.MOUSEMOTION and draw == True:
                    (actualX, actualY) = pygame.mouse.get_pos()
                    if (actualX < LEFT_MARGIN):
                        actualX = LEFT_MARGIN;
                    if (actualY < TOP_MARGIN):
                        actualY = TOP_MARGIN;
                    if (actualY > SCREEN_HEIGHT - TOP_MARGIN):
                        actualY = SCREEN_HEIGHT - TOP_MARGIN;
                    if prevX != 0 and prevY != 0:
                        await self.makeScreen(screen,False);
                        if len(all_lines) > 1:
                            pygame.draw.lines(screen, (0, 0, 0), False, all_lines, 5)
                        pygame.draw.line(screen, (0, 0, 0), (prevX, prevY), (actualX, actualY), 5)
                        pygame.display.flip()
                    else:
                        prevX, prevY = actualX, actualY
                        all_lines.append((prevX, prevY));

                if event.type == pygame.MOUSEBUTTONUP:
                    if draw == False:
                        continue;
                    (actualX, actualY) = pygame.mouse.get_pos()
                    if (actualX < LEFT_MARGIN):
                        actualX = LEFT_MARGIN;
                    if (actualY < TOP_MARGIN):
                        actualY = TOP_MARGIN;
                    if (actualY > SCREEN_HEIGHT - TOP_MARGIN):
                        actualY = SCREEN_HEIGHT - TOP_MARGIN;
                    prevX, prevY = actualX, actualY
                    all_lines.append((prevX, prevY));
                    draw = False

        prevPoint = (0, 0);
        prevRotation = 90;
        for point in all_lines:
            if (prevPoint[0] == 0 and prevPoint[1] == 0):
                prevPoint = point;
            else:
                delta_x = point[0] - prevPoint[0]
                delta_y = point[1] - prevPoint[1]
                angle = -atan2(delta_y, delta_x) * 180 / pi
                dist = sqrt(delta_x * delta_x + delta_y * delta_y);
                rotate_angle = angle - prevRotation;
                self.steps.append((COMMAND_ROTATE, rotate_angle));
                self.steps.append((COMMAND_MOVE, dist));
                prevPoint = point;
                prevRotation = angle;

        all_blocks = pygame.sprite.Group()

        self.cur_instruction = "Drag and drop events from the panel onto the path"

        block = Block(_panel_block=True,_action="arm")
        block.rect.x = 10;
        block.rect.y = 50;
        all_blocks.add(block)
        self.action_var["arm"] = "";

        block2 = Block(_panel_block=True, _action="face")
        block2.rect.x = 10;
        block2.rect.y = 150;
        all_blocks.add(block2)
        self.action_var["face"] = "";

        block3 = Block(_panel_block=True, _action="say")
        block3.rect.x = 10;
        block3.rect.y = 250;
        all_blocks.add(block3)
        self.action_var["say"] = "";

        block_text1 = TextBox((10, 105, 50, 30), prompt = "1.0", clear_on_enter=True, inactive_on_enter=False, active=True)
        block_text2 = TextBox((10, 205, 50, 30), prompt = "1.0", clear_on_enter=True, inactive_on_enter=False, active=False)
        block_text3 = TextBox((10, 305, 50, 30), prompt = "Hello", clear_on_enter=True, inactive_on_enter=False, active=False)
        block_text1.id = "arm"
        block_text2.id = "face"
        block_text3.id = "say"

        self.text_blocks = {}
        self.text_blocks[block_text1.id] = block_text1;
        self.text_blocks[block_text2.id] = block_text2;
        self.text_blocks[block_text3.id] = block_text3;

        await self.makeScreen(screen);
        if len(all_lines) > 1:
            pygame.draw.lines(screen, (0, 0, 0), False, all_lines, 5)
        all_blocks.draw(screen)
        for key, box in self.text_blocks.items():
            box.get_event(event)
            box.update()
            box.draw(screen)
        pygame.display.update()
        pygame.display.flip()

        drag = False
        drag_list = [];
        found_action = False
        while not found_action:
            for event in pygame.event.get():
                clock.tick(60)
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if (self.run_button != None and self.run_button.collidepoint(event.pos[0],event.pos[1])):
                        return True;
                    if (self.restart_button != None and self.restart_button.collidepoint(event.pos[0],event.pos[1])):
                        return False;
                    drag = True
                    for box in all_blocks:
                        if box.rect.collidepoint(event.pos[0], event.pos[1]):
                            if(box.panel_block == True):
                                var = self.getActionVariable(box.action);
                                new_box = Block(_panel_block=False,_action=box.action,_variable=var)
                                new_box.rect.x = box.rect.x;
                                new_box.rect.y = box.rect.y;
                                all_blocks.add(new_box);
                                all_blocks.draw(screen);
                                drag_list.append(new_box);
                            else:
                                drag_list.append(box);

                if event.type == pygame.MOUSEBUTTONUP:
                    if(event.pos[0] < LEFT_MARGIN or event.pos[1] < TOP_MARGIN or event.pos[1] > SCREEN_HEIGHT-TOP_MARGIN):
                        for box in drag_list:
                            all_blocks.remove(box)
                        await self.makeScreen(screen);
                        if len(all_lines) > 1:
                            pygame.draw.lines(screen, (0, 0, 0), False, all_lines, 5)
                        all_blocks.draw(screen)
                        for block in drag_list:
                            block.update();
                    else:
                        if len(drag_list) > 0:
                            self.checkIntersection(drag_list, all_lines);
                        print(self.steps);
                    drag = False
                    drag_list = []

                if event.type == pygame.MOUSEMOTION and drag == True:
                    await self.makeScreen(screen);
                    if len(all_lines) > 1:
                        pygame.draw.lines(screen, (0, 0, 0), False, all_lines, 5)
                    all_blocks.draw(screen)
                    for block in drag_list:
                        block.update();

                for key,box in self.text_blocks.items():
                    box.get_event(event)
                    box.update()
                    box.draw(screen)
                pygame.display.update()
                pygame.display.flip()
            pass;

    def getActionVariable(self, id):
        if(id == "say"):
            txt = self.text_blocks[id].getText();
            if txt != "":
                return txt;
            return "Hello";
        elif(id == "arm"):
            try:
                num = float(self.text_blocks[id].getText());
                if num > 0 and num < 1:
                    return num;
                elif num < 0:
                    return 0.0;
                else:
                    return 1.0
            except:
                return 1.0;
        elif (id == "face"):
            try:
                num = float(self.text_blocks[id].getText());
                if num > 0 and num < 1:
                    return num;
                elif num < 0:
                    return 0.0;
                else:
                    return 1.0
            except:
                return 1.0;

    def checkIntersection(self, blocks,lines):
        intersection = (0,0);
        block = blocks[0];
        prevPoint = (0,0);
        i=0;
        if (block.action_id != -1):
            index = self.steps.index((COMMAND_ACTION,(block.action_id,block.action,block.variable)))
            lines.remove(block.intersection_point);
            del self.steps[index]
            if (self.steps[index][0] == COMMAND_MOVE and self.steps[index - 1][0]):
                move1 = self.steps[index - 1][1];
                move2 = self.steps[index][1];
                self.steps[index - 1] = (COMMAND_MOVE, move1 + move2)
                del self.steps[index];
            block.action_id = -1;
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
            lines.insert(i, intersection);
            step_index = (i - 1) * 2 + 1;
            action_id = random.random();
            self.steps[step_index] = (COMMAND_MOVE, dist2);
            self.steps.insert(step_index,(COMMAND_ACTION,(action_id, block.action,block.variable)))
            self.steps.insert(step_index, (COMMAND_MOVE, dist3));
            block.action_id = action_id;
            block.intersection_point = intersection
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