import discord
from discord.ext import commands
import numpy as np
import random
from PIL import Image, ImageDraw
from io import BytesIO
import functools

#==================================================================================================================================================

class Tree:
    def __init__(self):
        self._root = self

    @property
    def root(self):
        _root = self._root
        while True:
            cur = getattr(_root, "_root")
            if cur is _root:
                break
            else:
                _root = cur
        self._root = _root
        return _root

    def connect(self, tree):
        self.root._root = tree.root

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

    def connect(self, xy1, xy2):
        i1 = self.ADJACENT.index((xy2[0]-xy1[0], xy2[1]-xy1[1]))
        i2 = 1-i1 if i1<2 else 5-i1
        self.data[xy1] = self.data[xy1] & ~(0b01 << (6-2*i1))
        self.data[xy2] = self.data[xy2] & ~(0b01 << (6-2*i2))

    @classmethod
    def prim_algorithm(cls, xy, *, weave=False, density=0):
        self = cls(xy)
        randrange = random.randrange
        choice = random.choice
        connect = self.connect
        neighbors = self.neighbors

        frontiers = []
        frontiers_check = set()
        maze_nodes = set()

        current = (randrange(self.xy[0]), randrange(self.xy[1]))
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
            connect(choice(current_maze_nodes), current)
            maze_nodes.add(current)
            frontiers.extend(current_frontiers)
            frontiers_check.update(current_frontiers)
        return self

    @classmethod
    def kruskal_algorithm(cls, xy, *, weave=False, density=0.05):
        self = cls(xy)
        randrange = random.randrange
        rand = random.random
        choice = random.choice
        connect = self.connect
        neighbors = self.neighbors

        all_nodes = {(x, y): Tree() for x, y in np.ndindex(*xy)}
        walls = []

        weave_gacha = (0b11110101, 0b01011111)
        for x, y in np.ndindex(*xy):
            if y < xy[1] - 1:
                walls.append((x, y, x, y+1))
            if x < xy[0] - 1:
                walls.append((x, y, x+1, y))
            if weave:
                if 0 < x < xy[0] - 1 and 0 < y < xy[1] - 1:
                    if rand() < density:
                        weaveable = choice(weave_gacha)
                        self.data[x, y] = self.data[x, y] & weaveable
                        for ix, iy in self.ADJACENT:
                            self.connect((x, y), (x+ix, y+iy))
                        walls = [w for w in walls if w not in ((x, y, x, y+1), (x, y, x+1, y), (x-1, y, x, y), (x, y-1, x, y))]
                        middle = all_nodes.pop((x, y))
                        for xy1, xy2 in (((x-1, y), (x+1, y)), ((x, y-1), (x, y+1))):
                            tree1 = all_nodes.get(xy1)
                            tree2 = all_nodes[xy2]
                            if tree1:
                                tree2.connect(tree1)
                            else:
                                tree2.connect(middle)

        while walls:
            index = randrange(len(walls))
            wall = walls.pop(index)
            xy1 = (wall[0], wall[1])
            xy2 = (wall[2], wall[3])
            tree1 = all_nodes[xy1]
            tree2 = all_nodes[xy2]
            if tree1.root is not tree2.root:
                connect(xy1, xy2)
                tree2.connect(tree1)

        return self

#==================================================================================================================================================

class MazeRunner:
    def __init__(self, ctx, maze, *, mode, weave, density):
        self.ctx = ctx
        self.player = ctx.author
        self.weave = weave
        self.maze = maze

    @classmethod
    async def new(cls, ctx, size, *, mode, weave, density):
        func = functools.partial(getattr(Maze, f"{mode}_algorithm"), (size, size), weave=weave, density=density)
        if mode == "kruskal" and size > 30 and weave:
            maze = await ctx.bot.loop.run_in_executor(None, func)
        else:
            maze = func()
        return cls(ctx, maze, mode=mode, weave=weave, density=density)

    async def draw_maze(self):
        def draw_non_weave():
            cell_size = 20

            yx = self.maze.xy
            xy = (yx[1]*cell_size, yx[0]*cell_size)
            image = Image.new("RGB", (xy[0]+11, xy[1]+11), (255, 255, 255))
            draw = ImageDraw.Draw(image)
            draw.line((5+xy[0], 5, 5, 5, 5, 5+xy[1]), width=1, fill=(0, 0, 0))

            for (iy, ix), v in np.ndenumerate(self.maze.data):
                if v % 0b10 > 0: #right wall
                    draw.line((5+(ix+1)*cell_size, 5+iy*cell_size, 5+(ix+1)*cell_size, 5+(iy+1)*cell_size), width=1, fill=(0, 0, 0))

                if (v >> 4) % 0b10 > 0: #down wall
                    draw.line((5+ix*cell_size, 5+(iy+1)*cell_size, 5+(ix+1)*cell_size, 5+(iy+1)*cell_size), width=1, fill=(0, 0, 0))

            draw.rectangle((6, 6, 4+cell_size, 4+cell_size), fill=(120, 255, 120), outline=None)
            draw.rectangle((6+xy[0]-cell_size, 6+xy[1]-cell_size, 4+xy[0], 4+xy[1]), fill=(255, 120, 120), outline=None)

            bytes_ = BytesIO()
            image.save(bytes_, "png")
            bytes_.seek(0)
            return bytes_

        def draw_weave():
            cell_size = 20
            space = 3
            path_size = cell_size - 2 * space

            yx = self.maze.xy
            xy = (yx[1]*cell_size, yx[0]*cell_size)
            image = Image.new("RGB", (xy[0]+1, xy[1]+1), (248, 248, 248))
            draw = ImageDraw.Draw(image)

            for (iy, ix), v in np.ndenumerate(self.maze.data):
                draw.rectangle((ix*cell_size+space, iy*cell_size+space, (ix+1)*cell_size-space, (iy+1)*cell_size-space), fill=(255, 255, 255))
                if v & 0b00000001 > 0: #right wall
                    draw.line(
                        (
                            (ix+1)*cell_size-space, iy*cell_size+space,
                            (ix+1)*cell_size-space, (iy+1)*cell_size-space
                        ), width=1, fill=(0, 0, 0)
                    )
                else:
                    draw.rectangle(((ix+1)*cell_size-space, iy*cell_size+space, (ix+1)*cell_size, (iy+1)*cell_size-space), fill=(255, 255, 255))
                    draw.line(((ix+1)*cell_size-space, iy*cell_size+space, (ix+1)*cell_size, iy*cell_size+space), width=1, fill=(0, 0, 0))
                    draw.line(((ix+1)*cell_size-space, (iy+1)*cell_size-space, (ix+1)*cell_size, (iy+1)*cell_size-space), width=1, fill=(0, 0, 0))

                if v & 0b00000100 > 0: #left wall
                    draw.line(
                        (
                            ix*cell_size+space, iy*cell_size+space,
                            ix*cell_size+space, (iy+1)*cell_size-space
                        ), width=1, fill=(0, 0, 0)
                    )
                else:
                    draw.rectangle((ix*cell_size, iy*cell_size+space, ix*cell_size+space, (iy+1)*cell_size-space), fill=(255, 255, 255))
                    draw.line((ix*cell_size, iy*cell_size+space, ix*cell_size+space, iy*cell_size+space), width=1, fill=(0, 0, 0))
                    draw.line((ix*cell_size, (iy+1)*cell_size-space, ix*cell_size+space, (iy+1)*cell_size-space), width=1, fill=(0, 0, 0))

                if v & 0b00010000 > 0: #down wall
                    draw.line(
                        (
                            ix*cell_size+space, (iy+1)*cell_size-space,
                            (ix+1)*cell_size-space, (iy+1)*cell_size-space
                        ), width=1, fill=(0, 0, 0)
                    )
                else:
                    draw.rectangle((ix*cell_size+space, (iy+1)*cell_size-space, (ix+1)*cell_size-space, (iy+1)*cell_size), fill=(255, 255, 255))
                    draw.line((ix*cell_size+space, (iy+1)*cell_size-space, ix*cell_size+space, (iy+1)*cell_size), width=1, fill=(0, 0, 0))
                    draw.line(((ix+1)*cell_size-space, (iy+1)*cell_size-space, (ix+1)*cell_size-space, (iy+1)*cell_size), width=1, fill=(0, 0, 0))

                if v & 0b01000000 > 0: #up wall
                    draw.line(
                        (
                            ix*cell_size+space, iy*cell_size+space,
                            (ix+1)*cell_size-space, iy*cell_size+space
                        ), width=1, fill=(0, 0, 0)
                    )
                else:
                    draw.rectangle((ix*cell_size+space, iy*cell_size, (ix+1)*cell_size-space, iy*cell_size+space), fill=(255, 255, 255))
                    draw.line((ix*cell_size+space, iy*cell_size, ix*cell_size+space, iy*cell_size+space), width=1, fill=(0, 0, 0))
                    draw.line(((ix+1)*cell_size-space, iy*cell_size, (ix+1)*cell_size-space, iy*cell_size+space), width=1, fill=(0, 0, 0))

                if v & 0b10100000 == 0:
                    draw.line((ix*cell_size+space, iy*cell_size+space, (ix+1)*cell_size-space, iy*cell_size+space), width=1, fill=(0, 0, 0))
                    draw.line((ix*cell_size+space, (iy+1)*cell_size-space, (ix+1)*cell_size-space, (iy+1)*cell_size-space), width=1, fill=(0, 0, 0))
                if v & 0b00001010 == 0:
                    draw.line(((ix+1)*cell_size-space, iy*cell_size+space, (ix+1)*cell_size-space, (iy+1)*cell_size-space), width=1, fill=(0, 0, 0))
                    draw.line((ix*cell_size+space, iy*cell_size+space, ix*cell_size+space, (iy+1)*cell_size-space), width=1, fill=(0, 0, 0))

            draw.rectangle((space+1, space+1, cell_size-space-1, cell_size-space-1), fill=(120, 255, 120))
            draw.rectangle((xy[0]-cell_size+space+1, xy[1]-cell_size+space+1, xy[0]-space-1, xy[1]-space-1), fill=(255, 120, 120))

            bytes_ = BytesIO()
            image.save(bytes_, "png")
            bytes_.seek(0)
            return bytes_

        return await self.ctx.bot.loop.run_in_executor(None, draw_weave if self.weave else draw_non_weave)
