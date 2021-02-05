import json
import os
import math
import random
import io
import asyncio

import discord
from discord.ext import commands
from PIL import Image


# config
if not (os.path.isfile(os.path.join(os.path.dirname(__file__), "config.json")) and os.path.isfile(os.path.join(os.path.dirname(__file__), "civs.json")) and os.path.isfile(os.path.join(os.path.dirname(__file__), "expansions.json"))):
    print("Could not find the correct configuration files.")
    input("Press enter to quit.")
    quit()
else:
    with open(os.path.join(os.path.dirname(__file__), "config.json")) as f:
        config = json.load(f)
    with open(os.path.join(os.path.dirname(__file__), "civs.json")) as f:
        civilizations = json.load(f)
    with open(os.path.join(os.path.dirname(__file__), "expansions.json")) as f:
        expansions = json.load(f)


# events
async def on_ready():
    print("Bot is ready.")
    await bot.change_presence(activity=discord.Game(name=config["activity"]))

    # random profile picture
    path = "images/flags/" + random.choice(civilizations["civs"])["picture"]
    img = Image.open(path)
    img = img.crop((28, 28, 172, 172))
    byte = io.BytesIO()
    img.save(byte, format="PNG")
    await bot.user.edit(avatar=byte.getvalue())



# bot
bot = commands.Bot(command_prefix=config["prefix"], help_command=None)

bot.add_listener(on_ready)


# functions
async def image_paths_to_bytes(paths):
    images = []

    for f in paths:
        images.append(Image.open(os.path.join(os.path.dirname(__file__), f)))

    combined_image = Image.new("RGBA", (len(paths) * images[0].width, images[0].height))
    
    for count, image in enumerate(images):
        combined_image.paste(image, (count * image.width, 0))

    combined_image = combined_image.resize((combined_image.width // 2, combined_image.height // 2))

    byte = io.BytesIO()
    combined_image.save(byte, format="PNG")
    byte.seek(0)

    return byte

def ban_check(ctx, msg, bans, ban_groups):
    content = msg.content.capitalize()
    if msg.channel.id != ctx.channel.id: return False
    if ctx.author != msg.author: return False
    if (content in [x["name"] for x in civilizations["civs"]] or content == "Finished" or content in ban_groups) and content not in bans: return True

# commands
@bot.command()
async def help(ctx):
    text = ("`>names` lists the names of civilisations\n"
            "`>standard` lists the names of civilisations in the standard ban\n"
            "`>bans` shows banning instructions\n"
            "`>tier [1-6]` lists the civilisations in a certain Filthy Robot tier\n"
            "`>[tiers|tierlist]` shows the entire Filthy Robot tier list\n"
            "`>draft` starts a civilisation draft\n"
            "`>draft [no_players] [no_civs_per_player]` quick draft command without bans")

    await ctx.send("**Help**")
    await ctx.send(text)


@bot.command()
async def names(ctx):
    await ctx.send("\n".join([civ["name"] for civ in civilizations["civs"]]))
  

@bot.command()
async def standard(ctx):
    await ctx.send("\n".join(config["standard_ban"]))


@bot.command()
async def bans(ctx):
    await ctx.send("Ban civilisations individually `>names`, ban tiers `>tiers` or use the standard ban `>standard`")


@bot.command()
async def tier(ctx, number):
    number = int(number)

    if (number > 6 or number < 1):
        return
    
    civs_in_tier = []

    for civ in civilizations["civs"]:
        if civ["tier"] == number:
            civs_in_tier.append(civ)
    
    flag_paths = ["images/flags/" + c["picture"] for c in civs_in_tier]
    names = [c["name"] for c in civs_in_tier]
    image_bytes = await image_paths_to_bytes(flag_paths)

    await ctx.send(f"**Tier {number}**")
    await ctx.send(", ".join(names))
    await ctx.send(file=discord.File(image_bytes, filename="tier.png"))


@bot.command(aliases=["tierlist"])
async def tiers(ctx):
    await tier(ctx, 1)
    await tier(ctx, 2)
    await tier(ctx, 3)
    await tier(ctx, 4)
    await tier(ctx, 5)
    await tier(ctx, 6)


@bot.command()
async def draft(ctx, no_players=None, no_civs_per_player=None):
    total_no_civs = len(civilizations["civs"])
    bans = []
    ban_groups = ["Standard", "Tier1", "Tier2", "Tier3", "Tier4", "Tier5", "Tier6"]

    if not no_players or not no_civs_per_player or not (no_players.isdigit() and no_civs_per_player.isdigit()):
        no_players = 0
        no_civs_per_player = 0
    else:
        no_players = int(no_players)
        no_civs_per_player = int(no_civs_per_player)
    
    if not (1 <= no_players <= 12 and 1 <= no_civs_per_player <= math.floor(total_no_civs/no_players)):
        # number of players input
        await ctx.send("How many players? (1-12)")

        player_check = lambda m : m.channel.id == ctx.channel.id and ctx.author == m.author and m.content.isdigit() and 1 <= int(m.content) <= 12
        no_players = int((await bot.wait_for("message", check=player_check)).content)

        # banned civs input
        await ctx.send(f"{no_players} players\nBanned civs? (check `>bans`)\nType `finished` after banning civs")

        check = lambda msg : ban_check(ctx, msg, bans, ban_groups)
        ban = (await bot.wait_for("message", check=check)).content.capitalize()

        while ban != "Finished":
            if ban == "Standard":
                ban_list = config["standard_ban"]
                for c in ban_list:
                    if c not in bans:
                        bans.append(c)
            elif "Tier" in ban:
                # check it is in the format TierX (5 characters long with Tier at the start)
                if len(ban) == 5:
                    tier_number = ban[4]
                    for c in civilizations["civs"]:
                        name = c["name"]
                        if name not in bans and str(c["tier"]) == tier_number:
                            bans.append(name)
            else:
                bans.append(ban)

            if len(bans) == 1:
                await ctx.send("1 civ has been banned")
            else:
                await ctx.send(f"{len(bans)} civs have been banned")

            ban = (await bot.wait_for("message", check=check)).content.capitalize()

        max_civs = math.floor((total_no_civs-len(bans))/no_players)

        if max_civs == 0:
            await ctx.send("No draft, all civs have been banned")
            return

        if len(bans) == 1:
            await ctx.send(f"{', '.join(bans)} (1 civ) has been banned")
        else:
            await ctx.send(f"{', '.join(bans)} ({len(bans)} civs) have been banned")

        await ctx.send(f"How many civs per player? (1-{max_civs})")
        
        civ_check = lambda m : m.channel.id == ctx.channel.id and ctx.author == m.author and m.content.isdigit() and 1 <= int(m.content) <= max_civs
        no_civs_per_player = int((await bot.wait_for("message", check=civ_check)).content)

        await ctx.send(f"{no_civs_per_player} civs per player")

    # rolling civs to draft
    async def roll():
        civ_choices = civilizations["civs"].copy()
        civ_choices = [c for c in civ_choices if c["name"] not in bans]

        for i in range(no_players):
            options = random.sample(civ_choices, no_civs_per_player)
            flag_paths = ["images/flags/" + o["picture"] for o in options]
            names = [o["name"] for o in options]
            civ_choices = [c for c in civ_choices if c not in options]

            image_bytes = await image_paths_to_bytes(flag_paths)

            await ctx.send(f"**Player {i+1}**")
            await ctx.send(", ".join(names))
            await ctx.send(file=discord.File(image_bytes, filename="draft.png"))
            
        # re-rolling
        reroll_message = await ctx.send("Redraft?")
        await reroll_message.add_reaction("🔁")

        def reroll_check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == "🔁" and reaction.message == reroll_message

        try:
            await bot.wait_for("reaction_add", timeout=120.0, check=reroll_check)
        except asyncio.TimeoutError:
            await reroll_message.delete()
        else:
            await roll()

    await roll()


bot.run(config["token"])
