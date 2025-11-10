import random
import asyncio
import subprocess
import logging
import os

from .utils import seconds_to_hms, get_top_three, record_game_success, song_txt, check_game_disable, isplayingcheck, filter_random, fault_tips, get_video_duration
from .music_model import gameplay_list, game_alias_map, alias_dict, total_list, continuous_stop
from .guess_song_chart import chart_total_list, id_mp4_file_map, id_mp3_file_map
from ..config import *

from nonebot import on_command
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent, MessageSegment


CLIP_DURATION = 30
GUESS_TIME = 90

guess_note = on_command("note猜歌", aliases={"note音猜歌"}, priority=5) 
continuous_guess_note = on_command("连续note猜歌", aliases={"连续note音猜歌"}, priority=5)


def make_note_sound(input_path, start_time, output_path):
    command = [
        "ffmpeg",
        "-i", input_path,
        "-ss", seconds_to_hms(start_time),
        "-t", str(CLIP_DURATION),
        "-q:a", "0",
        output_path
    ]
    try:
        logging.info("Cutting note sound...")
        subprocess.run(command, check=True)
        logging.info(f"Cutting completed. File saved as '{output_path}'.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error during cutting: {e}", exc_info=True)
    except Exception as ex:
        logging.error(f"An unexpected error occurred: {ex}", exc_info=True)
        
         
def note_rank_message(group_id):
    top_listen = get_top_three(group_id, "note")
    if top_listen:
        msg = "今天的前三名note音猜歌王：\n"
        for rank, (user_id, count) in enumerate(top_listen, 1):
            msg += f"{rank}. {MessageSegment.at(user_id)} 猜对了{count}首歌！\n"
        msg += "这都听得出，你们也是无敌了。。。"
        return msg


async def note_open_song_handler(matcher, song_name, group_id, user_id, ignore_tag):
    '''开歌处理函数'''
    (answer_music, start_time) = gameplay_list[group_id]["note"]
    random_music_id = answer_music.id
    is_remaster = False
    if int(random_music_id) > 500000:
        # 是白谱，需要找回原始music对象
        random_music_id = str(int(random_music_id) % 500000)
        is_remaster = True
    random_music = total_list.by_id(random_music_id)
    
    music_candidates = alias_dict.get(song_name)
    if music_candidates is None:
        if ignore_tag:
            return
        await matcher.finish("没有找到这样的乐曲。请输入正确的名称或别名", reply_message=True)
        return
    
    if len(music_candidates) < 20:
        for music_index in music_candidates:
            music = total_list.music_list[music_index]
            if random_music and random_music.id == music.id:
                gameplay_list.pop(group_id)
                record_game_success(user_id=user_id, group_id=group_id, game_type="note")
                reply_message = MessageSegment.text("恭喜你猜对啦！答案就是：\n") + song_txt(random_music, is_remaster) + "\n对应的片段如下："
                await matcher.send(Message(reply_message), reply_message=True)
                answer_input_path = id_mp3_file_map.get(answer_music.id)  # 这个是旧的id，即白谱应该找回白谱的id
                answer_output_path: Path = guess_resources_path / f"{group_id}_{start_time}_answer.mp3"
                await asyncio.to_thread(make_note_sound, answer_input_path, start_time, answer_output_path)
                await matcher.send(MessageSegment.record(f"file://{answer_output_path}"))
                os.remove(answer_output_path)
    if not ignore_tag:        
        await matcher.finish("你猜的答案不对噢，再仔细听一下吧！", reply_message=True)
        

@guess_note.handle()
async def _(event: GroupMessageEvent, matcher: Matcher, args: Message = CommandArg()):
    group_id = str(event.group_id)
    game_name = "note"
    if check_game_disable(group_id, game_name):
        await matcher.finish(f"本群禁用了{game_alias_map[game_name]}游戏，请联系管理员使用“/开启猜歌 {game_alias_map[game_name]}”来开启游戏吧！")
    await isplayingcheck(group_id, matcher)
    params = args.extract_plain_text().strip().split()
    await note_guess_handler(group_id, matcher, params)
    

@continuous_guess_note.handle()
async def _(event: GroupMessageEvent, matcher: Matcher, args: Message = CommandArg()):
    if len(chart_total_list) == 0:
        await matcher.finish("文件夹没有下载任何谱面视频资源，请让bot主尽快到 https://github.com/apshuang/nonebot-plugin-guess-song 下载资源吧！需要配置好谱面资源才能进行note音猜歌噢")
    group_id = str(event.group_id)
    game_name = "note"
    if check_game_disable(group_id, game_name):
        await matcher.finish(f"本群禁用了{game_alias_map[game_name]}游戏，请联系管理员使用“/开启猜歌 {game_alias_map[game_name]}”来开启游戏吧！")
    params = args.extract_plain_text().strip().split()
    await isplayingcheck(group_id, matcher)
    if not filter_random(chart_total_list, params, 1):
        await matcher.finish(fault_tips, reply_message=True)
    await matcher.send('连续note音猜歌已开启，发送\"停止\"以结束')
    continuous_stop[group_id] = 1
    while continuous_stop.get(group_id):
        if gameplay_list.get(group_id) is None:
            await note_guess_handler(group_id, matcher, params)
        if continuous_stop[group_id] > 3:
            continuous_stop.pop(group_id)
            await matcher.finish('没人猜了？ 那我下班了。')
        await asyncio.sleep(1)
        
        
async def note_guess_handler(group_id, matcher: Matcher, args):
    if len(chart_total_list) == 0:
        await matcher.finish("文件夹没有下载任何谱面视频资源，请让bot主尽快到 https://github.com/apshuang/nonebot-plugin-guess-song 下载资源吧！需要配置好谱面资源才能进行note音猜歌噢")
    if _ := filter_random(chart_total_list, args, 1):
        random_music = _[0]
    else:
        await matcher.finish(fault_tips, reply_message=True)
    input_path = id_mp4_file_map.get(random_music.id)
    video_duration = get_video_duration(input_path)
    if not video_duration or CLIP_DURATION > video_duration - 15:
        raise ValueError(f"截取时长不能超过视频总时长减去15秒")
    
    start_time = random.uniform(5, video_duration - CLIP_DURATION - 10)
    output_path: Path = guess_resources_path / f"{group_id}_{start_time}.mp3"
    await asyncio.to_thread(make_note_sound, input_path, start_time, output_path)
    msg = "这首歌的谱面截取的一个片段的note音如下，请回复\"猜歌xxx\"提交您认为在答案中的曲目（可以是歌曲的别名），或回复\"不猜了\"来停止游戏"
    if len(args):
        msg += f"\n本次note音猜歌范围：{', '.join(args)}"
    await matcher.send(msg)
    gameplay_list[group_id] = {}
    gameplay_list[group_id]["note"] = (random_music, start_time)

    # 发送语音到群组
    await matcher.send(MessageSegment.record(f"file://{output_path}"))
    os.remove(output_path)
    
    for _ in range(GUESS_TIME):
        await asyncio.sleep(1)
        if gameplay_list.get(group_id) is None or not gameplay_list[group_id].get("note") or gameplay_list[group_id].get("note") != random_music:
            if continuous_stop.get(group_id):
                continuous_stop[group_id] = 1
            return
        
    answer_music_id = random_music.id
    random_music_id = random_music.id
    is_remaster = False
    if int(random_music_id) > 500000:
        # 是白谱，需要找回原始music对象
        random_music_id = str(int(random_music_id) % 500000)
        is_remaster = True
    random_music = total_list.by_id(random_music_id)
    gameplay_list.pop(group_id)
    if random_music:
        reply_message = MessageSegment.text("很遗憾，你没有猜到答案，正确的答案是：\n") + song_txt(random_music, is_remaster) + "\n对应的片段如下："
    await matcher.send(reply_message)
    answer_input_path = id_mp3_file_map.get(answer_music_id)  # 这个是旧的id，即白谱应该找回白谱的id
    answer_output_path: Path = guess_resources_path / f"{group_id}_{start_time}_answer.mp3"
    await asyncio.to_thread(make_note_sound, answer_input_path, start_time, answer_output_path)
    await matcher.send(MessageSegment.record(f"file://{answer_output_path}"))
    os.remove(answer_output_path)
    if continuous_stop.get(group_id):
        continuous_stop[group_id] += 1