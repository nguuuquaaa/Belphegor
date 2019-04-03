import discord
from discord.ext import commands
import numpy as np
import random
from PIL import Image, ImageDraw
from io import BytesIO

#==================================================================================================================================================

class Maze:
    ADJACENT = ((-1, 0), (1, 0), (0, -1), (0, 1))

    def __init__(self, xy):
        self.xy = xy
        self.data = np.full(xy, 0b11111111, dtype=np.uint8)
        self.solution = None

    def neighbors(self, xy):
        x, y = xy
        base_x, base_y = self.xy
        for ix, iy in self.ADJACENT:
            cx = x + ix
            cy = y + iy
            if 0 <= cx < base_x and 0 <= cy < base_y:
                yield cx, cy

    def connect(self, xy1, xy2, height=1):
        i1 = self.ADJACENT.index((xy2[0]-xy1[0], xy2[1]-xy1[1]))
        i2 = 1-i1 if i1<2 else 5-i1
        self.data[xy1] = self.data[xy1] & ~((0b11-(height<<1)) << (6-2*i1))
        self.data[xy2] = self.data[xy2] & ~((0b11-(height<<1)) << (6-2*i2))

    @classmethod
    def prim_algorithm(cls, xy):
        obj = cls(xy)
        frontiers = []
        frontiers_check = set()
        maze_nodes = set()
        randrange = random.randrange
        choice = random.choice
        neighbors = obj.neighbors
        connect = obj.connect

        current = (randrange(obj.xy[0]), randrange(obj.xy[1]))
        maze_nodes.add(current)
        n = tuple(neighbors(current))
        frontiers.extend(n)
        frontiers_check.update(n)

        while frontiers:
            current = frontiers.pop(randrange(len(frontiers)))
            frontiers_check.remove(current)
            current_frontiers = []
            current_maze_nodes = []
            for node in neighbors(current):
                if node in maze_nodes:
                    current_maze_nodes.append(node)
                elif node not in frontiers_check:
                    current_frontiers.append(node)
            connect(current, choice(current_maze_nodes))
            maze_nodes.add(current)
            frontiers.extend(current_frontiers)
            frontiers_check.update(current_frontiers)
        return obj

#==================================================================================================================================================

class MazeRunner:
    def __init__(self, ctx, player, xy=(20, 20), mode="prim"):
        self.ctx = ctx
        self.player = player
        self.maze = getattr(Maze, f"{mode}_algorithm")(xy)

    async def draw_maze(self):
        def do_stuff():
            cell_size = 20
            yx = self.maze.xy
            xy = (yx[1]*cell_size, yx[0]*cell_size)
            image = Image.new("RGB", (xy[0]+11, xy[1]+11), (255, 255, 255))
            draw = ImageDraw.Draw(image)
            draw.rectangle((5, 5, 5+cell_size, 5+cell_size), fill=(120, 255, 120), outline=None)
            draw.rectangle((5+xy[0]-cell_size, 5+xy[1]-cell_size, 5+xy[0], 5+xy[1]), fill=(255, 120, 120), outline=None)
            draw.line((5+xy[0], 5, 5, 5, 5, 5+xy[1]), width=1, fill=(0, 0, 0))
            for (iy, ix), v in np.ndenumerate(self.maze.data):
                down = v % 0b10
                if down:
                    draw.line((5+(ix+1)*cell_size, 5+iy*cell_size, 5+(ix+1)*cell_size, 5+(iy+1)*cell_size), width=1, fill=(0, 0, 0))
                right = (v >> 4) % 0b10
                if right:
                    draw.line((5+ix*cell_size, 5+(iy+1)*cell_size, 5+(ix+1)*cell_size, 5+(iy+1)*cell_size), width=1, fill=(0, 0, 0))

            bytes_ = BytesIO()
            image.save(bytes_, "png")
            bytes_.seek(0)
            return bytes_

        return await self.ctx.bot.loop.run_in_executor(None, do_stuff)
