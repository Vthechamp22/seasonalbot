# NOTE: https://www.mockaroo.com/ can be good for random JSON
# TODO: Make the quotations all the same
# TODO: Comment everything
# TODO: one emoji from one user

# Importing everything

import asyncio
import json
import logging
import random
import time
from pathlib import Path

import discord
from discord.channel import TextChannel
from discord.ext import commands, tasks
from discord.ext.commands import Cog
from discord.ext.commands.bot import Bot
from discord.ext.commands.context import Context

from bot.constants import Channels
from bot.constants import Client
from bot.constants import Colours
from bot.constants import Month
from bot.utils.decorators import in_month


logger = logging.getLogger(__name__)


class SpookNameRate(Cog):
    """
    A game that asks the user to spookify or halloweenify a name that is given everyday.

    It sends a random name everyday. The user needs to try and spookify it to his best ability and
    send that word back using the `spooknamerate add entry` command

    Parameters:
        - bot: A discord.ext.commands.bot.Bot instance which represents the Discord Bot

    Returns:
        - None
    """

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.messages = {}  # a variable to store all the messages
        self.emojis_val = {  # the value of the emojis
            '🎃': 1,
            '👻': 2,
            '☠': 3,
            '🧟': 4,
            '😱': 5
        }
        json_data = self.load_json(Path('bot', 'resources', 'halloween', 'spooknamerate.json'))  # load the JSON
        self.first_names = json_data['first_names']  # get the first
        self.last_names = json_data['last_names']  # and last
        # the names are from https://www.name-generator.org.uk/quick/

        self.first = True
        self.poll = False
        self.channel_id = Channels.seasonalbot_commands
        self.announce_word.start()

    @in_month(Month.OCTOBER)
    @commands.group(name="spooknamerate", invoke_without_command=True)
    async def spook_name_rate(self, ctx: Context) -> None:
        """Get help on the Spook Name Rate game."""
        # Send an embed with help on the command

        help_embed = discord.Embed(
            title="Spook Name Rate",
            description=f"Help on the `{self.bot.command_prefix}spooknamerate` command",
            color=Colours.soft_orange,
        )

        emoji_message = ""
        for emoji in self.emojis_val:
            emoji_message += f"- {emoji} {self.emojis_val.get(emoji)}\n"

        help_embed.add_field(
            name="How to play",
            value=f"""Everyday, the bot will post a random word, which you will need to spookify using your creativity.
You can rate each message according to how scary it is
At the end of the day, the author of the message with most reactions will be the winner of the day.
On a scale of 1 to {len(self.emojis_val)}, the reactions order:
{emoji_message}""",
            inline=False
        )

        help_embed.add_field(
            name="How do I add my spookified word?",
            value=f"Just simply type `{self.bot.command_prefix}spooknamerate add my word`",
            inline=False
        )

        await ctx.send(embed=help_embed)

    @spook_name_rate.command(name='list', aliases=["all", "entries"])
    async def list_entries(self, ctx: Context) -> None:
        """Send all the entries up till now in a single embed."""
        await ctx.send(embed=await self.get_responses_list(final=False))

    @spook_name_rate.command(name="add", aliases=["+", "register"])
    async def add_word(self, ctx: Context, *, word: str) -> None:
        """A command that adds your word!"""
        if not self.poll:
            message = ctx.message  # get the message

            for message_id in self.messages:
                data = self.messages.get(message_id)
                if data['author'] == message.author:  # if the author has already added an entry
                    return await ctx.send(f"But you have already added an entry! Type `{self.bot.command_prefix}spooknamerate \
delete` to delete it, and then you can add it again")

            # otherwise
            self.messages[message.id] = {  # and store it
                'word': word,  # store the word
                'author': message.author,  # and the author
                'score': 0,  # and the score
            }

            for emoji in self.emojis_val.keys():  # get the emojis
                await message.add_reaction(emoji)  # and add them

            logger.info(f"{message.author} added the word {word!r}")
            return await ctx.send(f"{word!r} added successfullly! Let's see if you win?")  # TODO: ADD RESPONSES
        else:
            logger.info(f"{ctx.message.author} tried to add a word, but the poll had already started.")
            await ctx.send("Sorry, the poll has started! You can try and participate in the next round though!")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member) -> None:
        """Ensures that each user adds one and only one reaction."""
        try:
            if reaction.emoji in self.emojis_val.keys():
                for data in self.messages.values():
                    for reaction in reaction.message.reactions:
                        if reaction.emoji in self.emojis_val.keys():
                            if reaction.count > 1:
                                pass
                        # if user == data['author']:
                        #     print(user, data)
                        #     return await reaction.remove(user)
        except RuntimeError:  # The dictionary was changed in between
            pass

    @spook_name_rate.command(name='delete')
    async def delete_word(self, ctx: Context) -> None:
        """Delete's the user's word."""
        for message_id in self.messages.keys():
            data = self.messages[message_id]
            if ctx.author == data['author']:
                del self.messages[message_id]
                if self.messages.get(message_id) is None:
                    await ctx.send(f'Message deleted successfully ({data["word"]}!')
                else:
                    return ctx.send("Oops, there was some error, please try again!")

    @tasks.loop(seconds=60.0)  # TODO: hours=24.0)
    async def announce_word(self) -> None:
        """Announces the name needed to spookify every 24 hours and the winner of the previous game."""
        test_perf = time.perf_counter()
        channel = await self.get_channel()
        logger.info(f"Time slept: {time.perf_counter() - test_perf:0.2f}")

        if self.first:
            # await self.bot.wait_until_ready()  # TODO: Check if necessary
            for message in ["Okkey... Welcome to Spook Name Rate! It's a relatively simple game.",
                            "Everyday, a random name will be sent in #seasonalbot-commands",
                            f"And you need to try and spookify it! Register your word using \
`{self.bot.command_prefix}spooknamerate add spookified_name`"]:
                await channel.send(message)
                await asyncio.sleep(1)
            self.first = False  # Now it isn't the first time.

        else:  # otherwise,
            if len(self.messages) > 0:  # Only if there is a player
                await channel.send(embed=await self.get_responses_list(final=True))  # send the responses
                self.poll = True  # start polling
                await asyncio.sleep(30)  # TODO: sleep for 2 hours

            logger.info('Calculating score')
            for message_id in self.messages:
                msg = await channel.fetch_message(message_id)  # fetch the message
                score = 0
                reactions = msg.reactions  # get the reactions
                for reaction in reactions:
                    reaction_value = self.emojis_val.get(reaction.emoji, 0)  # get the value of the emoji else 0
                    score += reaction_value * (reaction.count - 1)  # multiply by the num of reactions
                    # subtract one, since one reaction was done by the bot

                logger.debug(f'{msg.author} got a score of {score}')
                self.messages[message_id]['score'] = score

            winner_messages = sorted(self.messages.items(), key=lambda x: x[1]['score'], reverse=True)

            # Sort the winner messages
            winners = []
            for i, winner in enumerate(winner_messages):
                winners.append(winner)
                if len(winner_messages) > i + 1:
                    if winner_messages[i + 1][1]['score'] != winner[1]['score']:
                        break
                elif len(winner_messages) == (i + 1) + 1:  # The next element is the last element and len() returns the entire length
                    if winner_messages[i + 1][1]['score'] != winner[1]['score']:
                        break

            await channel.send("Today's Spook Name Rate Game ends now, and the winner(s) is(are)...")

            async with channel.typing():
                await asyncio.sleep(1)  # give the drum roll feel

                if len(winners) > 0:  # make sure there is a winner
                    # TODO: Check if tie is working

                    if len(winners) > 1:  # if there are more than one winners
                        await channel.send(" and ".join([win[1]['author'].mention for win in winners]) + " !")
                        score = winners[0][1]['score']
                        await channel.send(f"Congratulations to all! You have a score of {score}!")
                        wrds = ', '.join([f'{win[1]["word"]} ({win[1]["author"].mention})' for win in winners])
                        await channel.send(f"Your words were: {wrds}!")

                    else:  # if there is only one winner
                        # There cant be 0 winners since we are checking that above

                        winner = winners[0][1]
                        await channel.send(f"{winner['author'].mention}!")
                        await channel.send(f"Congratulations to {winner['author'].mention}! You have a score of \
{winner['score']}!")
                        await channel.send(f"Your word was: **{winner['word']}**.")

                    # Send random party emojis
                    party = [random.choice([':partying_face:', ':tada:']) for _ in range(random.randint(1, 10))]
                    await channel.send(" ".join(party))

                else:  # if there isn't a winner
                    await channel.send('Hmm... Looks like no one participated! :cry:')

            self.messages = {}  # reset the messages

        # send the next name
        async with channel.typing():
            for message in ["Anyways... let's move on to the next name!",
                            "And the next name is...",  # And today's name is...
                            f"**{random.choice(self.first_names)} {random.choice(self.last_names)}**!",
                            "Try to spookify that... :smirk:"]:
                await asyncio.sleep(0.7)
                await channel.send(message)

        self.poll = False  # Now accepting responses

    async def get_responses_list(self, final: bool = False) -> discord.Embed:
        """Returns an embed containing the responses of the people."""
        channel = await self.get_channel()

        embed = discord.Embed(
            color=Colours.red,
            title="",
            description=""
        )

        if len(self.messages) > 0:
            if final:  # if it is the final
                embed.title = "Spook Name Rate is about to end!"
                embed.description = "This Spook Name Rate round is about to end in 2 hours! You can review \
    the entries below! Have you rated other's words?"
            else:
                embed.title = "All the spookified names!"
                embed.description = "See a list of all the entries entered by everyone!"
        else:
            embed.title = "No one has added an entry yet..."

        for message in self.messages:
            data = self.messages.get(message)

            embed.add_field(
                name=data['author'],
                value=f"[{data['word']}](https://discord.com/channels/{Client.guild}/{channel.id}/{message})",
            )

        return embed

    async def get_channel(self) -> TextChannel:
        """Gets the seasonalbot-channel after waiting until ready."""
        await self.bot.wait_until_ready()
        return self.bot.get_channel(self.channel_id)

    @staticmethod
    def load_json(file: Path) -> dict:
        """Loads a JSON file and returns its contents."""
        with file.open('r', encoding='utf-8') as f:
            return json.load(f)


def setup(bot: commands.Bot) -> None:
    """Loads the SpookNameRate Cog."""
    bot.add_cog(SpookNameRate(bot))
