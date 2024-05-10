import os
import discord
from discord.ext import commands
from llm_magic import (
    add_video_to_memory,
    get_and_persist_youtube_transcript,
    get_file_type,
    injest_file,
    chat_collection,
    replace_specials_with_underscores,
    add_url_to_memory,
)
from database import FileManager, SqliteDatabase

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
bot.heartbeat_timeout = 900
started = False
SAVE_DIRECTORY = "files"
DATABASE_PATH = "database.db"


chosen_file = ""
file_owner = "Generic"
chosen_store = ""

def embeded_text(string: str, title: str) -> discord.Embed:
    embed = discord.Embed(title=title)
    embed.add_field(name=string, value="\u200b", inline=False)
    return embed

@bot.command(name="choose-owner")
async def choose_owner(ctx, owner):
    global file_owner
    file_owner = owner
    await ctx.send(embed=embeded_text(f"Owner changed to {owner}!", "Owner changed!"))

@bot.command(name="choose-file")
async def choose(ctx, store_name, file_name):
    global chosen_file, file_owner, chosen_store
    
    filenames = [
        file.file_name
        for file in FileManager(SqliteDatabase(DATABASE_PATH)).get_all_files_for_collection(
            file_owner=file_owner,
            store_name=store_name
        )
    ]
    if file_name in filenames:
        chosen_file = file_name
        chosen_store = store_name
        await ctx.send("FIle chosen")
    else:
        await ctx.send("No such file exists.")

@bot.command(name="delete-file")
async def delete_file(ctx, store_name, file_name):
    global chosen_file, file_owner, chosen_store

    model = FileManager(SqliteDatabase(DATABASE_PATH)).get_cls()
    if files := tuple(model.select().where(model.file_owner == file_owner and model.store_name == store_name and model.file_name == file_name)):
        files[0].delete_instance()
        await ctx.send("FIle deleted")
    else:
        await ctx.send("No such file exists.")

@bot.command(name="add-link")
async def add_link(ctx, link, store_name):
    global file_owner
    
    sanitized_filename = f"{file_owner}_{store_name}_{replace_specials_with_underscores(link)}"
    if (
        not link.startswith("youtube.com/watch?v=")
        and not link.startswith("https://www.youtube.com/watch?v=")
        and not link.startswith("http://www.youtube.com/watch?v=")
        and not link.startswith("https://youtu.be/")
        and not link.startswith("http://youtu.be/")
    ):
        content = await add_url_to_memory(link, sanitized_filename)
    else:
        content = get_and_persist_youtube_transcript(
            sanitized_filename, link
        )
        
    FileManager(SqliteDatabase(DATABASE_PATH)).create_file(
        file_owner, link, None, content, sanitized_filename, store_name=store_name
    )
    await ctx.send(f"Successfully received {link}.. Processed link")

@bot.command(name="upload")
async def upload(ctx, store_name: str):
    if len(ctx.message.attachments) <= 0:
        return
    
    global file_owner
    for attachment in ctx.message.attachments:
        sanitized_filename = replace_specials_with_underscores(
            f"{file_owner}_{store_name}_{attachment.filename}"
        )
        save_path = os.path.join(
            SAVE_DIRECTORY,
            sanitized_filename,
        )
        await attachment.save(save_path)
        await ctx.send(
            f"Successfully received {attachment.filename}.. Processing file"
        )
        content = (
            add_video_to_memory(
                index_name=sanitized_filename,
                filename=save_path,
                source=save_path.split("/")[-1],
            )
            if get_file_type(save_path) in {"video", "audio"}
            else injest_file(save_path, index_name=f"{sanitized_filename}")
        )
        FileManager(SqliteDatabase(DATABASE_PATH)).create_file(
            file_owner, attachment.filename, None, content, sanitized_filename, store_name
        )
        await ctx.send(f"Processed file {attachment.filename}")
        os.remove(save_path)

@bot.command(name="list-subjects")
async def list(ctx):
    global file_owner
    
    files = FileManager(SqliteDatabase(DATABASE_PATH)).get_all_collections_for_owner(
        owner_name=file_owner
    )
    embed = discord.Embed(title=f"Available Subjects Owner ({file_owner}):")
    for i, file in enumerate(files, start=1):
        embed.add_field(
            name=f"{i}. {file}",
            value="\u200b",
            inline=False,
        )        
    await ctx.send(embed=embed)
    
@bot.command(name="list-files")
async def list_files(ctx, store_name=None):
    global file_owner
    
    if store_name:
        embed = discord.Embed(title=f"Available Files Owner ({file_owner}):")
        files = FileManager(SqliteDatabase(DATABASE_PATH)).get_all_files_for_collection(
            file_owner=file_owner,
            store_name=store_name
        )
        
        for i, file in enumerate(files, start=1):
            embed.add_field(
                name=f"{i}. {file.file_name}",
                value="\u200b",
                inline=False,
            )        
    else:
        embed = discord.Embed(title=f"Available Files Owner ({file_owner} - {store_name}):")
        files = FileManager(SqliteDatabase(DATABASE_PATH)).get_all_files_for_owner(
            file_owner=file_owner
        )
        for i, file in enumerate(files, start=1):
            embed.add_field(
                name=f"{i}. {file.file_name} ({file.store_name})",
                value="\u200b",
                inline=False,
            )        
        
    await ctx.send(embed=embed)
    
@bot.command(name="commands")
async def commands(ctx):
    embed = discord.Embed(title="Available Commands")
    embed.add_field(
        name="1. list",
        value="Lists All the available files",
        inline=False,
    )
    embed.add_field(
        name="2. choose-file",
        value="Allows the user to choose a file",
        inline=False,
    )
    embed.add_field(
        name="2. chat",
        value="Allows the user to chat with the file",
        inline=False,
    )
    await ctx.send(embed=embed)

@bot.command(name="chat")
async def chat(ctx, *message):
    global file_owner, chosen_store
    pk = f"{file_owner}_{chosen_store}_{replace_specials_with_underscores(chosen_file)}"
    await ctx.send(
        chat_collection(
            chat_history=[],
            index_name=pk,
            question=" ".join(message),
        )["answer"],
    )


if __name__ == "__main__":
    from config import BOTTOKEN
    bot.run(BOTTOKEN)
