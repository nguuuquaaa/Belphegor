import discord
from discord.ext import commands
import numpy as np
import random
from PIL import Image, ImageDraw
from io import BytesIO
import functools
import collections
import asyncio

#==================================================================================================================================================

class Tree:
    __slots__ = ("_root",)

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

    def __init__(self, data):
        self.data = data
        self.xy = data.shape

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
        self.data[xy1] &= ~(0b01000000 >> 2*i1)
        self.data[xy2] &= ~(0b01000000 >> 2*i2)

    @classmethod
    def prim_algorithm(cls, xy, *, weave=False, density=0):
        data = np.full(xy, 0b11111111, dtype=np.uint8)
        self = cls(data)
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
        data = np.full(xy, 0b11111111, dtype=np.uint8)
        self = cls(data)
        randrange = random.randrange
        rand = random.random
        choice = random.choice
        connect = self.connect
        adjacent = self.ADJACENT

        all_nodes = {(x, y, i): Tree() for x, y, i in np.ndindex(*xy, 2)}
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
                        for ix, iy in adjacent:
                            connect((x, y), (x+ix, y+iy))
                        walls = [w for w in walls if w not in ((x, y, x, y+1), (x, y, x+1, y), (x-1, y, x, y), (x, y-1, x, y))]

                        if weaveable == 0b11110101:
                            all_nodes[(x, y, 1)], all_nodes[(x, y, 0)] = all_nodes[(x, y, 0)], all_nodes[(x, y, 1)]
                        for i, (x1, y1, x2, y2) in enumerate(((x-1, y, x+1, y), (x, y-1, x, y+1))):
                            v1 = self.data[x1, y1]
                            h1 = (v1 >> (5-4*i)) & 0b01
                            tree1 = all_nodes[(x1, y1, h1)]
                            tree2 = all_nodes[(x2, y2, i)]
                            h = (weaveable >> (5-4*i)) & 0b01
                            middle = all_nodes[(x, y, h)]
                            middle.connect(tree1)
                            tree2.connect(tree1)
                        continue
            all_nodes[(x, y, 0)].connect(all_nodes[(x, y, 1)])

        while walls:
            index = randrange(len(walls))
            x1, y1, x2, y2 = walls.pop(index)
            tree1 = all_nodes[(x1, y1, 1)]
            tree2 = all_nodes[(x2, y2, 1)]
            if tree1.root is not tree2.root:
                connect((x1, y1), (x2, y2))
                tree2.connect(tree1)

        return self

    def movable(self, xyh):
        x, y, h = xyh
        v = self.data[x, y]
        for i in range(4):
            if (v >> (6-2*i)) & 0b01 == 0 and (v >> (7-2*i)) & 0b01 == h:
                ix, iy = self.ADJACENT[i]
                nx = x + ix
                ny = y + iy
                nv = self.data[nx, ny]
                yield (ix, iy), (nx, ny, (nv >> (7-2*i)) & 0b01)

    def solve(self):
        movable = self.movable
        adjacent = self.ADJACENT

        out = (self.xy[0]-1, self.xy[1]-1, 1)
        solution = {(0, 0, 1): (None, None)}
        stack = collections.deque([(0, 0, 1)])
        while True:
            current = stack.pop()
            for ixy, nxyh in movable(current):
                if nxyh in solution:
                    continue
                solution[nxyh] = (current, ixy)
                if nxyh == out:
                    break
                stack.append(nxyh)
            else:
                continue
            break

        ret = collections.deque()
        cur = out
        while True:
            cur, val = solution[cur]
            if cur:
                ret.appendleft(val)
            else:
                break
        return ret

#==================================================================================================================================================

class MazeRunner:
    CELL_SIZE = 20
    WEAVE_CELL_SPACE = 3

    def __init__(self, player, maze, *, mode, weave, density):
        self.player = player
        self.weave = weave
        self.maze = maze
        self.rendering = None

    @classmethod
    async def new(cls, ctx, size, *, mode, weave, density, loop=None):
        func = functools.partial(getattr(Maze, f"{mode}_algorithm"), (size, size), weave=weave, density=density)
        if mode == "kruskal" and size > 30 and weave:
            loop = loop or asyncio.get_event_loop()
            maze = await loop.run_in_executor(None, func)
        else:
            maze = func()
        return cls(ctx.author, maze, mode=mode, weave=weave, density=density)

    def _raw_draw(self):
        def draw_non_weave():
            cell_size = self.CELL_SIZE

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

            return image

        def draw_weave():
            cell_size = self.CELL_SIZE
            space = self.WEAVE_CELL_SPACE
            path_size = cell_size - 2 * space

            yx = self.maze.xy
            xy = (yx[1]*cell_size, yx[0]*cell_size)
            image = Image.new("RGB", (xy[0]+1, xy[1]+1), (224, 224, 224))
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

            return image

        if self.rendering is None:
            image = draw_weave() if self.weave else draw_non_weave()
            self.rendering = np.array(image)
        return Image.fromarray(self.rendering)

    async def draw_maze(self, loop=None):
        def draw_it():
            image = self._raw_draw()
            bytes_ = BytesIO()
            image.save(bytes_, "png")
            bytes_.seek(0)
            return bytes_

        loop = loop or asyncio.get_event_loop()
        return await loop.run_in_executor(None, draw_it)

    async def draw_solution(self, loop=None):
        def draw_it():
            solution = self.maze.solve()
            image = self._raw_draw()
            draw = ImageDraw.Draw(image)
            movable = self.maze.movable
            current = (0, 0, 1)
            shift = 0 if self.weave else 5
            cell_size = self.CELL_SIZE
            half_passage = cell_size // 2 - self.WEAVE_CELL_SPACE

            current_point_x = shift + cell_size // 2
            current_point_y = shift + cell_size // 2
            for move in solution:
                for ixy, nxyh in movable(current):
                    if ixy == move:
                        break

                next_point_x = current_point_x + cell_size * ixy[0]
                next_point_y = current_point_y + cell_size * ixy[1]
                minus_current = half_passage*(1-current[2])
                minus_nxyh = half_passage*(1-nxyh[2])
                draw.line(
                    (
                        current_point_y+minus_current*ixy[1], current_point_x+minus_current*ixy[0],
                        next_point_y-minus_nxyh*ixy[1], next_point_x-minus_nxyh*ixy[0]
                    ), fill=(0, 0, 160), width=3
                )

                current = nxyh
                current_point_x = next_point_x
                current_point_y = next_point_y

            bytes_ = BytesIO()
            image.save(bytes_, "png")
            bytes_.seek(0)
            return bytes_

        loop = loop or asyncio.get_event_loop()
        return await loop.run_in_executor(None, draw_it)
