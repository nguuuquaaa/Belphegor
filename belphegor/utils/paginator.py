import discord
from discord.ext import commands
import collections
import traceback
import asyncio

#==================================================================================================================================================

class Everyone:
    def __bool__(self):
        return True

    def __eq__(self, item):
        return not item.bot

    def __contains__(self, item):
        return not item.bot

#==================================================================================================================================================

EVERYONE = Everyone()

#==================================================================================================================================================

class Paginator:
    def __init__(self, container, per_page=1, *, separator="\n", jump=10, book=False, page_display=True, **kwargs):
        self.container = container
        self.per_page = per_page
        self.separator = separator
        self.book = book
        self.jump = jump
        self.page_display = page_display
        self.render_data = kwargs
        if book:
            self._item_amount = []
            self.page_amount = []
            for c in container:
                l = len(c)
                self._item_amount.append(c)
                self.page_amount.append((l - 1) // per_page + 1)
        else:
            self._item_amount = len(container)
            self.page_amount = (len(container) - 1) // per_page + 1

        self.current_page = 0
        self.current_book = 0 if book else None
        self.book_amount = len(container) if book else 1
        self._setup_base_reactions()
        self.cached_embeds = {}

    def get_page_amount(self, book=None):
        if self.current_book is None:
            return self.page_amount
        else:
            book = book or self.current_book
            return self.page_amount[book]

    def go_left(self):
        self.current_page = max(self.current_page-1, 0)
        return self.render()

    def go_right(self):
        self.current_page = min(self.current_page+1, self.get_page_amount()-1)
        return self.render()

    def jump_left(self):
        self.current_page = max(self.current_page-self.jump, 0)
        return self.render()

    def jump_right(self):
        self.current_page = min(self.current_page+self.jump, self.get_page_amount()-1)
        return self.render()

    def go_up(self):
        self.current_book = max(self.current_book-1, 0)
        self.current_page = min(self.current_page, self.get_page_amount()-1)
        return self.render()

    def go_down(self):
        self.current_book = min(self.current_book+1, self.book_amount-1)
        self.current_page = min(self.current_page, self.get_page_amount()-1)
        return self.render()

    def _setup_base_reactions(self):
        self.navigation = collections.OrderedDict()
        if (self.book and max(self.page_amount) > 1) or (not self.book and self.page_amount > 1):
            self.navigation["\u23ee"] = Paginator.jump_left
            self.navigation["\u25c0"] = Paginator.go_left
            self.navigation["\u25b6"] = Paginator.go_right
            self.navigation["\u23ed"] = Paginator.jump_right
        if self.book_amount > 1:
            self.navigation["\U0001f53c"] = Paginator.go_up
            self.navigation["\U0001f53d"] = Paginator.go_down
        if self.navigation:
            self.navigation["\u274c"] = lambda s: None

    def set_action(self, emoji, func):
        if emoji != "\u274c":
            self.navigation[emoji] = func
            try:
                self.navigation.move_to_end("\u274c")
            except KeyError:
                self.navigation["\u274c"] = lambda s: None

    def render(self):
        page = self.current_page
        book = self.current_book
        cached_render = self.cached_embeds.get((page, book))
        if cached_render:
            return cached_render

        render_data = self.render_data
        Empty = discord.Embed.Empty

        if book is None:
            container = self.container
            per_page = self.per_page
            item_amount = self._item_amount
            page_amount = self.page_amount
        else:
            container = self.container[book]
            per_page = self.per_page[book]
            item_amount = self._item_amount[book]
            page_amount = self.page_amount[book]
            book_amount = len(self.container)

        title = render_data.get("title")
        if callable(title):
            if book:
                t = title(page, book)
            else:
                t = title(page)
        else:
            t = title
        url = render_data.get("url")
        if callable(url):
            if book:
                u = url(page, book)
            else:
                u = url(page)
        else:
            u = url
        embed = discord.Embed(
            title=t or Empty,
            url=u or Empty,
            colour=render_data.get("colour", Empty)
        )

        prefix = render_data.get("prefix")
        if callable(prefix):
            if book:
                pf = prefix(page, book)
            else:
                pf = prefix(page)
        else:
            pf = prefix or ""

        suffix = render_data.get("suffix")
        if callable(suffix):
            if book:
                sf = suffix(page, book)
            else:
                sf = suffix(page)
        else:
            sf = suffix or ""

        description = render_data.get("description")
        fields = render_data.get("fields")
        desc = []
        index = page * per_page

        for i in range(index, min(index+per_page, item_amount)):
            if book is None:
                if description:
                    if callable(description):
                        desc.append(description(i, container[i]))
                    else:
                        desc.append(description)
                if fields:
                    name, value, inline = fields(i, container[i])
                    if name and value:
                        embed.add_field(name=name, value=value, inline=inline)
                paging = f"Page {page+1}/{page_amount}"
            else:
                if description:
                    if callable(description):
                        desc.append(description(i, container[i], book))
                    else:
                        desc.append(description)
                if fields:
                    name, value, inline = fields(i, container[i], book)
                    if name and value:
                        embed.add_field(name=name, value=value, inline=inline)
                paging = f"Page {page+1}/{page_amount} - Book {book+1}/{book_amount}"

        embed.description = self.separator.join(desc) or Empty

        author = render_data.get("author")
        if author:
            embed.set_author(name=author, icon_url=render_data.get("author_icon", Empty))

        thumbnail_url = render_data.get("thumbnail_url")
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)

        image_url = render_data.get("image_url")
        if callable(image_url):
            if book:
                imgur = image_url(page, book)
            else:
                imgur = image_url(page)
        else:
            imgur = image_url
        if imgur:
            embed.set_image(url=imgur)

        footer = render_data.get("footer")
        if callable(footer):
            if book:
                f = footer(page, book)
            else:
                f = footer(page)
        else:
            f = footer
        if self.page_display:
            embed.set_footer(text=f"({paging}) \u25fd {footer}" if footer else paging)
        else:
            embed.set_footer(text=footer or Empty)

        self.cached_embeds[(page, book)] = embed
        return embed

    async def navigate(self, ctx, *, timeout=60, target=None):
        _bot = ctx.bot
        _loop = _bot.loop
        target = target or ctx.author
        embed = self.render()
        message = await ctx.send(embed=embed)
        for e in self.navigation:
            _loop.create_task(message.add_reaction(e))

        async def try_it(coro):
            try:
                await coro
            except:
                pass

        try:
            while True:
                try:
                    reaction, user = await _bot.wait_for(
                        "reaction_add",
                        check=lambda r, u: target==u and r.emoji in self.navigation and r.message.id==message.id,
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    return
                embed = self.navigation[reaction.emoji](self)
                if embed:
                    await message.edit(embed=embed)
                    _loop.create_task(try_it(message.remove_reaction(reaction, user)))
                else:
                    return
        except asyncio.CancelledError:
            return
        finally:
            _loop.create_task(try_it(message.clear_reactions()))
