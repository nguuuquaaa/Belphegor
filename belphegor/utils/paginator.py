import discord
from discord.ext import commands
import collections
import traceback
import asyncio
import inspect

#==================================================================================================================================================

async def try_it(coro):
    try:
        await coro
    except:
        pass

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
    all_tasks = {}

    def __init__(self, container, per_page=1, *, separator="\n", jump=10, book=False, page_display=True, render=True, first_page=None, **kwargs):
        self.container = container
        self.per_page = per_page
        self.separator = separator
        self.book_mode = book
        self.jump = jump
        self.page_display = page_display
        self.first_page = first_page

        if book:
            self._item_amount = []
            self._page_amount = []
            for c in container:
                l = len(c)
                self._item_amount.append(l)
                self._page_amount.append((l - 1) // per_page + 1)
        else:
            self._item_amount = len(container)
            self._page_amount = (len(container) - 1) // per_page + 1

        if render is True:
            self.render = self._from_item
        elif render is False:
            self.render = self._prerender
            self._page_amount = self._item_amount
        elif callable(render):
            self.render = render
        else:
            raise TypeError("Render is either boolean or a callable.")

        self.render_data = kwargs
        self.current_page = 0
        self.current_book = 0 if book else None
        self.book_amount = len(container) if book else 1
        self._setup_base_actions()

    def get_page_amount(self, book=None):
        if self.book_mode:
            book = book or self.current_book
            return self._page_amount[book]
        else:
            return self._page_amount

    def get_item_amount(self, book=None):
        if self.book_mode:
            book = book or self.current_book
            return self._item_amount[book]
        else:
            return self._item_amount

    def _go_left(self):
        self.current_page = max(self.current_page-1, 0)
        return self.render()

    def _go_right(self):
        self.current_page = min(self.current_page+1, self.get_page_amount()-1)
        return self.render()

    def _jump_left(self):
        self.current_page = max(self.current_page-self.jump, 0)
        return self.render()

    def _jump_right(self):
        self.current_page = min(self.current_page+self.jump, self.get_page_amount()-1)
        return self.render()

    def _go_up(self):
        self.current_book = max(self.current_book-1, 0)
        self.current_page = min(self.current_page, self.get_page_amount()-1)
        return self.render()

    def _go_down(self):
        self.current_book = min(self.current_book+1, self.book_amount-1)
        self.current_page = min(self.current_page, self.get_page_amount()-1)
        return self.render()

    def _setup_base_actions(self):
        self.navigation = collections.OrderedDict()
        if (self.book_mode and max(self._page_amount) > 1) or (not self.book_mode and self._page_amount > 1):
            self.navigation["\u23ee"] = self._jump_left
            self.navigation["\u25c0"] = self._go_left
            self.navigation["\u25b6"] = self._go_right
            self.navigation["\u23ed"] = self._jump_right
        if self.book_amount > 1:
            self.navigation["\U0001f53c"] = self._go_up
            self.navigation["\U0001f53d"] = self._go_down
        if self.navigation:
            self.navigation["\u274c"] = lambda: None

    def set_action(self, emoji, func):
        if emoji != "\u274c":
            self.navigation[emoji] = func
            try:
                self.navigation.move_to_end("\u274c")
            except KeyError:
                self.navigation["\u274c"] = lambda: None

    def _prerender(self):
        if self.book_mode:
            c = self.container[self.current_book]
        else:
            c = self.container
        return c[self.current_page]

    def _from_item(self):
        page = self.current_page
        book = self.current_book
        book_mode = self.book_mode
        render_data = self.render_data
        Empty = discord.Embed.Empty
        per_page = self.per_page

        if book_mode:
            container = self.container[book]
            item_amount = self._item_amount[book]
            page_amount = self._page_amount[book]
            book_amount = len(self.container)
        else:
            container = self.container
            item_amount = self._item_amount
            page_amount = self._page_amount

        parts = {}
        for key in ("title", "url", "colour", "prefix", "suffix", "author", "thumbnail_url", "image_url", "footer"):
            subject = render_data.get(key)
            if callable(subject):
                if book_mode:
                    value = subject(page, book)
                else:
                    value = subject(page)
            else:
                value = subject
            parts[key] = value

        embed = discord.Embed(
            title=parts.get("title") or Empty,
            url=parts.get("url") or Empty,
            colour=parts.get("colour") or Empty
        )

        description = render_data.get("description")
        fields = render_data.get("fields")
        desc = []
        index = page * per_page

        for i in range(index, min(index+per_page, item_amount)):
            if book_mode:
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
            else:
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

        if desc:
            embed.description = f"{parts.get('prefix') or ''}\n{self.separator.join(desc)}\n{parts.get('suffix') or ''}"

        author = parts.get("author")
        if author:
            embed.set_author(name=author, icon_url=render_data.get("author_icon") or Empty)

        thumbnail_url = parts.get("thumbnail_url")
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)

        image_url = parts.get("image_url")
        if image_url:
            embed.set_image(url=image_url)

        footer = parts.get("footer")
        if self.page_display:
            embed.set_footer(text=f"({paging}) \u25fd {footer}" if footer else f"({paging})")
        else:
            embed.set_footer(text=footer or Empty)

        return embed

    async def add_navigate_reactions(self, message):
        for e in self.navigation:
            await message.add_reaction(e)

    async def navigate(self, ctx, *, timeout=60, target=None):
        _bot = ctx.bot
        _loop = _bot.loop
        target = target or ctx.author

        if target.id in self.all_tasks:
            self.all_tasks.pop(target.id).cancel()
        self.all_tasks[target.id] = asyncio.current_task(loop=_loop)

        if ctx.channel.permissions_for(ctx.me).manage_messages:
            event = "reaction_add"
            handle_reaction = lambda m, r, u: _loop.create_task(try_it(m.remove_reaction(r, u)))
        else:
            event = "reaction_add_or_remove"
            handle_reaction = lambda m, r, u: None
        if self.first_page:
            embed = self.first_page
        elif self.container:
            embed = self.render()
        else:
            embed = next(iter(self.navigation.values()))()
        try:
            message = await ctx.send(embed=embed)
        except asyncio.CancelledError:
            return self.all_tasks.pop(target.id)
        if not self.navigation:
            return self.all_tasks.pop(target.id)
        rt = _loop.create_task(self.add_navigate_reactions(message))

        try:
            while True:
                try:
                    reaction, user = await _bot.wait_for(
                        event,
                        check=lambda r, u: target==u and r.emoji in self.navigation and r.message.id==message.id,
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    return self.all_tasks.pop(target.id)
                embed = self.navigation[reaction.emoji]()
                if inspect.isawaitable(embed):
                    embed = await embed
                if embed:
                    await message.edit(embed=embed)
                    handle_reaction(message, reaction, user)
                else:
                    return self.all_tasks.pop(target.id)
        except asyncio.CancelledError:
            rt.cancel()
        finally:
            _loop.create_task(try_it(message.clear_reactions()))
