import asyncio
from audiosub2 import AudioSub 
import discord
from discord.ext import commands, voice_recv
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
import os

discord.opus._load_default()
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix = "$", intents=intents)
model = ChatOllama(model="llama3.2:3b", temperature=0.5)
connections = {}

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    await bot.process_commands(message)

@bot.command()
async def chatai(ctx: commands.Context, *, prompt: str):
    """
    Responds to a prompt using the ChatOllama model.
    Usage: $chatai <your prompt here>
    """
    print(f'{ctx.author} invoked the chatai command with prompt: {prompt}')
    
    response = model.invoke(prompt).content

    # split messages into chunks of 2000 characters
    chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
    for chunk in chunks:
        await ctx.send(chunk)

@bot.command()
async def fart(ctx: commands.Context):
    print(f'{ctx.author} invoked the fart command')
    await ctx.send(f'{ctx.author.mention} farted! 💨') # sends a message in the channel where the command was invoked


@bot.command()
async def join(ctx):
    channel = ctx.author.voice.channel
    if channel is None:
        await ctx.send("join a vc first")
        return
    await channel.connect(cls=voice_recv.VoiceRecvClient)

@bot.command()
async def leave(ctx):
    if ctx.voice_client is not None:
        await ctx.voice_client.disconnect()
        

@bot.command()
async def play(ctx, file: str):
    vchannel = ctx.author.voice.channel
    if vchannel is None:
        await ctx.send("You need to be in a voice channel to play audio.")
        return
    
    audio_src = "assets\\" + file + ".mp3"
    if not os.path.exists(audio_src):
        await ctx.send(f"Audio file '{file}' not found.")
        return
    
    await play_audio(vchannel, audio_src)

async def play_audio(vchannel, filename: str):
    vclient = await vchannel.connect(cls=voice_recv.VoiceRecvClient)

    src = discord.FFmpegPCMAudio(source=filename, executable='C:\\ffmpeg-7.1.1-full_build\\ffmpeg-7.1.1-full_build\\bin\\ffmpeg.exe')
    vclient.play(src)
    
    while vclient.is_playing():
        await asyncio.sleep(.1)
    await vclient.disconnect()


@bot.command()
async def record(ctx):  # If you're using commands.Bot, this will also work.
    voice = ctx.author.voice

    if not voice:
        await ctx.send("You aren't in a voice channel!")

    vc = await voice.channel.connect()  # Connect to the voice channel the author is in.
    connections.update({ctx.guild.id: vc})  # Updating the cache with the guild and channel.

    vc.start_recording(
        discord.sinks.WaveSink(),  # The sink type to use.
        once_done,  # What to do once done.
        ctx.channel  # The channel to disconnect from.
    )
    await ctx.send("Started recording!")

async def once_done(sink: discord.sinks, channel: discord.TextChannel, *args):  # Our voice client already passes these in.
    recorded_users = [  # A list of recorded users
        f"<@{user_id}>"
        for user_id, audio in sink.audio_data.items()
    ]

    await sink.vc.disconnect()  # Disconnect from the voice channel.
    files = [discord.File(audio.file, f"{user_id}.{sink.encoding}") for user_id, audio in sink.audio_data.items()]  # List down the files.

    for user_id, audio in sink.audio_data.items():
        with open(f"assets\\{user_id}-output.wav", "wb") as f:  # Open the recorded audio file.
            f.write(audio.file.getbuffer())  # Write the audio data to the file.

    await channel.send(f"finished recording audio for: {', '.join(recorded_users)}.", files=files)  # Send a message with the accumulated files.
    AS = AudioSub("assets")  # Create an instance of AudioSub with the directory where audio files are stored.
    await channel.send(AS.transcribe())

    # delete files in assets directory
    for file in os.listdir("assets"):
        if file.endswith(".wav"):
            os.remove(os.path.join("assets", file))
    

@bot.command()
async def stop_recording(ctx):
    if ctx.guild.id in connections:  # Check if the guild is in the cache.
        vc = connections[ctx.guild.id]
        vc.stop_recording()  # Stop recording, and call the callback (once_done).
        del connections[ctx.guild.id]  # Remove the guild from the cache.
        await ctx.message.delete()  # And delete.
    else:
        await ctx.send("I am currently not recording here.")  # Respond with this if we aren't recording.

load_dotenv()
token = os.getenv('DISCORD_BOT_TOKEN')
bot.run(token)