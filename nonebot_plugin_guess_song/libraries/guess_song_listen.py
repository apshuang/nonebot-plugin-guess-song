import random
import asyncio
from pydub import AudioSegment # 请注意，这里还需要ffmpeg，请自行安装

from .utils import *
from .music_model import gameplay_list, game_alias_map, alias_dict, total_list, continuous_stop

from nonebot import on_fullmatch, on_command
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER


guess_listen = on_command("听歌猜曲", aliases={"听歌辩曲"}, priority=5)    
continuous_guess_listen = on_command('连续听歌猜曲')
check_listen_file_completeness = on_command("检查歌曲文件完整性", permission=SUPERUSER)

listen_total_list: List[Music] = []

def extract_random_clip(music_file, duration_ms=10000):
    song = AudioSegment.from_file(music_file)
    song_length = len(song)
    if song_length <= duration_ms:
        return song
    start_ms = random.randint(0, song_length - duration_ms)
    end_ms = start_ms + duration_ms
    clip = song[start_ms:end_ms]
    return clip


def save_clip_as_audio(clip, output_file):
    '''将截取的片段保存为音频文件'''
    clip.export(output_file, format="mp3", bitrate="320k", parameters=["-ar", "44100"])
    

def listen_rank_message(group_id):
    top_listen = get_top_three(group_id, "listen")
    if top_listen:
        msg = "今天的前三名猜歌王：\n"
        for rank, (user_id, count) in enumerate(top_listen, 1):
            msg += f"{rank}. {MessageSegment.at(user_id)} 猜对了{count}首歌！\n"
        msg += "一堆wmc。。。"
        return msg


async def listen_open_song_handler(matcher, song_name, group_id, user_id, ignore_tag):
    '''开歌处理函数'''
    listen_info = gameplay_list.get(group_id).get("listen")
    music_candidates = alias_dict.get(song_name)
    if music_candidates is None:
        if ignore_tag:
            return
        await matcher.finish("没有找到这样的乐曲。请输入正确的名称或别名", reply_message=True)
    
    if len(music_candidates) < 20:
        for music_index in music_candidates:
            music = total_list.music_list[music_index]
            if listen_info.id == music.id:
                gameplay_list.pop(group_id)
                record_game_success(user_id=user_id, group_id=group_id, game_type="listen")
                reply_message = MessageSegment.text("恭喜你猜对啦！答案就是：\n") + song_txt(music)
                await matcher.finish(Message(reply_message), reply_message=True)
    if not ignore_tag:        
        await matcher.finish("你猜的答案不对噢，再仔细听一下吧！", reply_message=True)


@guess_listen.handle()
async def _(event: GroupMessageEvent, matcher: Matcher, args: Message = CommandArg()):
    group_id = str(event.group_id)
    game_name = "listen"
    if check_game_disable(group_id, game_name):
        await matcher.finish(f"本群禁用了{game_alias_map[game_name]}游戏，请联系管理员使用“/开启猜歌 {game_alias_map[game_name]}”来开启游戏吧！")
    params = args.extract_plain_text().strip().split()
    await isplayingcheck(group_id, matcher)
    await listen_guess_handler(group_id, matcher, params)

@continuous_guess_listen.handle()
async def _(event: GroupMessageEvent, matcher: Matcher, args: Message = CommandArg()):
    if len(listen_total_list) == 0:
        await matcher.finish("文件夹没有配置任何音乐资源，请让bot主尽快到 https://github.com/apshuang/nonebot-plugin-guess-song 下载资源吧！")
    group_id = str(event.group_id)
    game_name = "listen"
    if check_game_disable(group_id, game_name):
        await matcher.finish(f"本群禁用了{game_alias_map[game_name]}游戏，请联系管理员使用“/开启猜歌 {game_alias_map[game_name]}”来开启游戏吧！")
    params = args.extract_plain_text().strip().split()
    await isplayingcheck(group_id, matcher)
    if not filter_random(listen_total_list, params, 1):
        await matcher.finish(fault_tips, reply_message=True)
    await matcher.send('连续听歌猜曲已开启，发送\"停止\"以结束')
    continuous_stop[group_id] = 1
    while continuous_stop.get(group_id):
        if gameplay_list.get(group_id) is None:
            await listen_guess_handler(group_id, matcher, params)
        if continuous_stop[group_id] > 3:
            continuous_stop.pop(group_id)
            await matcher.finish('没人猜了？ 那我下班了。')
        await asyncio.sleep(1)

async def listen_guess_handler(group_id, matcher: Matcher, args):
    if len(listen_total_list) == 0:
        await matcher.finish("文件夹没有配置任何音乐资源，请让bot主尽快到 https://github.com/apshuang/nonebot-plugin-guess-song 下载资源吧！")
    if _ := filter_random(listen_total_list, args, 1):
        random_music = _[0]
    else:
        await matcher.finish(fault_tips, reply_message=True)
    music_file = get_music_file_path(random_music)
    if not os.path.isfile(music_file):
        await matcher.finish(f"文件夹中没有{random_music.title}的音乐文件，请让bot主尽快补充吧！")

    await matcher.send("这首歌截取的一个片段如下，请回复\"猜歌xxx\"提交您认为在答案中的曲目（可以是歌曲的别名），或回复\"不猜了\"来停止游戏", reply_message=True)
    gameplay_list[group_id] = {}
    gameplay_list[group_id]["listen"] = random_music

    clip = extract_random_clip(music_file)
    
    output_file = f"./{group_id}clip.mp3"
    output_file = convert_to_absolute_path(output_file)
    save_clip_as_audio(clip, output_file)

    # 发送语音到群组
    await matcher.send(MessageSegment.record(f"file://{output_file}"))
    os.remove(output_file)
    
    for _ in range(30):
        await asyncio.sleep(1)
        if gameplay_list.get(group_id) is None or not gameplay_list[group_id].get("listen") or gameplay_list[group_id].get("listen") != random_music:
            if continuous_stop.get(group_id):
                continuous_stop[group_id] = 1
            return
        
    gameplay_list.pop(group_id)
    reply_message = MessageSegment.text("很遗憾，你没有猜到答案，正确的答案是：\n") + song_txt(random_music)
    await matcher.send(reply_message)
    if continuous_stop.get(group_id):
        continuous_stop[group_id] += 1
            
        
@check_listen_file_completeness.handle()
async def check_listen_files(matcher: Matcher):
    mp3_files = []
    for filename in os.listdir(music_file_path):
        if filename.endswith(".mp3"):
            mp3_files.append(filename.replace(".mp3", ""))
    mp3_lost_files = []
    for music in total_list.music_list:
        music_file_name = (int)(music.id)
        music_file_name %= 10000
        music_file_name = str(music_file_name)
        if music_file_name not in mp3_files:
            mp3_lost_files.append(music_file_name)
    if len(mp3_lost_files) == 0:
        await matcher.finish("听歌猜曲的所有文件均完整，请放心进行听歌猜曲")
    if len(mp3_lost_files) != 0:
        await matcher.send(f"当前一共缺失了{len(mp3_lost_files)}首mp3文件，缺失的歌曲id如下{','.join(mp3_lost_files)}")


async def init_listen_guess_list():
    if not music_file_path.is_dir():
        # 如果没有配置猜歌资源，则跳过
        return
    mp3_files = []
    for filename in os.listdir(music_file_path):
        if filename.endswith(".mp3"):
            mp3_files.append(filename.replace(".mp3", ""))
    for music in total_list.music_list:
        # 过滤出有资源的music
        music_file_name = (int)(music.id)
        music_file_name %= 10000
        music_file_name = str(music_file_name)
        if music_file_name in mp3_files:
            listen_total_list.append(music)
            

asyncio.run(init_listen_guess_list())