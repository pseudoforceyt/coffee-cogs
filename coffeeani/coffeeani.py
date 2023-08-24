from redbot.core import Config, app_commands, commands, checks
from redbot.core.utils.views import SimpleMenu
import asyncio
import datetime
import json
import re
import aiohttp
import discord

from .utils import *

class Coffeeani(commands.Cog):
    """Search anime, manga (manhwa/manhua/light novels), users, and characters from Anilist. See series info, status, episodes/chapters, and tags."""

    def __init__(self):
        self.url = URL

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete."""
        return
        
    async def discord_anilist_embeds(self, ctx, cmd, entered_title):
        embed_data, data = await search_anime_manga(cmd, entered_title, isDiscord=True)

        if len(embed_data) <= 0:
            return None

        embeds = []
        idx_total = len(embed_data)
        for idx, am in enumerate(embed_data):
            embed = discord.Embed(title=am["title"])
            embed.url = am["link"]
            embed.color = 3447003
            embed.description = am["embed_description"]
            embed.set_image(url=am["image"])

            if am["info"]:
                embed.add_field(name=str(am["info_status"]), value=str(am["info"]), inline=True)
            if am["studios"]:
                embed.add_field(name="Studios", value=am["studios"], inline=True)
            if am["external_links"]:
                embed.add_field(name="Links", value=am["external_links"], inline=True)
            if am["names"]:
                embed.add_field(name="Names", value=am["country_of_origin_flag_str"]+description_parser(', '.join(am["names"])), inline=True)
            if am["tags"]:
                tags_inline = True
                if len(am["tags"]) > 11:
                    tags_inline = False
                embed.add_field(name="Tags", value=", ".join(am["tags"]), inline=tags_inline)
            if cmd == "ANIME":
                embed.set_footer(text=" ・ ".join(filter(None, [" ".join(filter(None, [am["info_format"], am["info_start_year"]])), am["time_left"], "Powered by Anilist", str(idx+1)+"/"+str(idx_total)])))
            else:
                embed.set_footer(text=" ・ ".join(filter(None, [" ".join(filter(None, [am["info_format"], am["info_start_year"]])), "Powered by Anilist", str(idx+1)+"/"+str(idx_total)])))
            embeds.append({"embed": embed})
        return embeds

    async def search_character(self, ctx, entered_title):

        variables = {"search": entered_title, "page": 1}

        data = (await request(SEARCH_CHARACTER_QUERY, variables))["data"]["Page"]["characters"]

        if data is not None and len(data) > 0:

            # a list of embeds
            embeds = []

            for character in data:
                # Sets up various variables for Embed
                link = f"https://anilist.co/character/{character['id']}"
                character_anime = [f'[{anime["title"]["userPreferred"]}]({"https://anilist.co/anime/" + str(anime["id"])})' for anime in character["media"]["nodes"] if anime["type"] == "ANIME"]
                character_manga = [f'[{manga["title"]["userPreferred"]}]({"https://anilist.co/manga/" + str(manga["id"])})' for manga in character["media"]["nodes"] if manga["type"] == "MANGA"]
                embed = discord.Embed(title=format_name(character["name"]["first"], character["name"]["last"]))
                embed.url = link
                embed.color = 3447003
                embed.description = description_parser(character["description"])
                embed.set_thumbnail(url=character["image"]["large"])
                if len(character_anime) > 0:
                    embed.add_field(name="Anime", value="\n".join(list_maximum(character_anime)))
                if len(character_manga) > 0:
                    embed.add_field(name="Manga", value="\n".join(list_maximum(character_manga)))
                embed.set_footer(text="Powered by Anilist")
                embeds.append(embed)

            return embeds, data

        else:
            return None

    async def search_user(self, ctx, entered_title):

        variables = {"search": entered_title, "page": 1}

        data = (await request(SEARCH_USER_QUERY, variables))["data"]["Page"]["users"]

        if data is not None and len(data) > 0:

            # a list of embeds
            embeds = []

            for user in data:
                # Sets up various variables for Embed
                link = f"https://anilist.co/user/{user['id']}"
                title = f"[{user['name']}]({link})"
                title = user["name"]

                embed = discord.Embed(title=title)
                embed.url = link
                embed.color = 3447003
                embed.description = description_parser(user["about"])
                embed.set_thumbnail(url=user["avatar"]["large"])
                embed.add_field(name="Watched time", value=datetime.timedelta(minutes=int(user["stats"]["watchedTime"])))
                embed.add_field(name="Chapters read", value=user["stats"].get("chaptersRead", "N/A"))
                for category in "anime", "manga", "characters":
                    fav = []
                    for node in user["favourites"][category]["nodes"]:
                        url_path = category
                        if category == "characters":
                            name = node["name"]
                            title = format_name(name["first"], name["last"])
                            url_path = "character"  # without the s
                        else:
                            title = node["title"]["userPreferred"]

                        fav.append(f'[{title}](https://anilist.co/{url_path}/{node["id"]})')

                    if fav:
                        embed.add_field(name=f"Favorite {category}", value="\n".join(list_maximum(fav)))
                embed.set_footer(text="Powered by Anilist")
                embeds.append(embed)

            return embeds, data

        else:
            return None


    @commands.hybrid_command()
    @app_commands.describe(title="Search for anime")
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def anime(self, ctx, *, title):
        """Searches for anime using Anilist"""
        entered_title = title

        try:
            cmd = "ANIME"
            embeds = await self.discord_anilist_embeds(ctx, cmd, entered_title)

            if embeds is not None:
                await SimpleMenu(pages=embeds, timeout=90).start(ctx)
            else:
                await ctx.send("No anime was found or there was an error in the process")

        except TypeError as e:
            print("Error:", e)
            await ctx.send("No anime was found or there was an error in the process")

    @commands.hybrid_command(aliases=["manhwa", "manhua", "lightnovel"])
    @app_commands.describe(title="Search for manga/manhwa/manhua and light novels")
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def manga(self, ctx, *, title):
        """Searches for manga, manhwa, manhua, and light novels using Anilist"""
        entered_title = title

        try:
            cmd = "MANGA"
            embeds = await self.discord_anilist_embeds(ctx, cmd, entered_title)

            if embeds is not None:
                await SimpleMenu(pages=embeds, timeout=90).start(ctx)
            else:
                await ctx.send("No mangas/manhwas/manhuas or light novels were found or there was an error in the process")

        except TypeError:
            await ctx.send("No mangas/manhwas/manhuas or light novels were found or there was an error in the process")

    @commands.hybrid_command(name="animecharacter", aliases=["animechar"])
    @app_commands.describe(name="Search for an anime/manga character")
    async def character(self, ctx, *, name):
        """Searches for characters using Anilist"""
        entered_title = name

        try:
            embeds, data = await self.search_character(ctx, entered_title)

            if embeds is not None:
                await SimpleMenu(pages=embeds, timeout=90).start(ctx)
            else:
                await ctx.send("No characters were found or there was an error in the process")

        except TypeError:
            await ctx.send("No characters were found or there was an error in the process")

    @commands.hybrid_group(name="anilist")
    async def anilist(self, ctx: commands.Context):
        """Search Anilist"""
        if not ctx.invoked_subcommand:
            pass

    @anilist.command(name="user")
    @app_commands.describe(username="Search Anilist for a user")
    async def user(self, ctx, *, username: str):
        """Searches users using Anilist"""
        entered_title = username

        try:
            embeds, data = await self.search_user(ctx, entered_title)

            if embeds is not None:
                await SimpleMenu(pages=embeds, timeout=90).start(ctx)
            else:
                await ctx.send("No users were found or there was an error in the process")

        except TypeError:
            await ctx.send("No users were found or there was an error in the process")
