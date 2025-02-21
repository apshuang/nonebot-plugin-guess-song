import random
import asyncio
from PIL import Image
from pydub import AudioSegment # 请注意，这里还需要ffmpeg，请自行安装

from .utils import *
from .music_model import gameplay_list, game_alias_map, alias_dict, total_list, Music, continuous_stop
from .guess_cover import image_to_base64

from nonebot import on_fullmatch, on_command
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent
from nonebot.params import CommandArg


guess_clue = on_command("线索猜歌", aliases={"猜歌"}, priority=5)    
continuous_guess_clue = on_command('连续线索猜歌')

async def pic(path: str) -> Image.Image:
    """裁切曲绘"""
    im = Image.open(path)
    w, h = im.size
    w2, h2 = int(w / 3), int(h / 3)
    l, u = random.randrange(0, int(2 * w / 3)), random.randrange(0, int(2 * h / 3))
    im = im.crop((l, u, l + w2, u + h2))
    return im


async def get_clues(music: Music):
    clue_list = [
        f'的 Expert 难度是 {music.level[2]}',
        f'的分类是 {music.genre}',
        f'的版本是 {music.version}',
        f'的 BPM 是 {music.bpm}',
        f'的紫谱有 {music.charts[3].note_sum} 个note，而且有 {music.charts[3].brk} 个绝赞'
    ]
    vital_clue = [
        f'的 Master 难度是 {music.level[3]}',
        f'的艺术家是 {music.artist}',
        f'的紫谱谱师为{music.charts[3].charter}',
    ]
    title = list(music.title)
    random.shuffle(title)
    title = ''.join(title)
    final_clue = f'的歌名组成为{title}'

    if music_file_path:
        # 若有歌曲文件，就加入歌曲长度作为线索
        music_file = get_music_file_path(music)
        try:
            song = AudioSegment.from_file(music_file)
            song_length = len(song) / 1000
            
            clue_list.append(f'的歌曲长度为 {int(song_length/60)}分{int(song_length%60)}秒')
        except Exception as e:
            print(e)
            
    # 特殊属性加入重要线索
    if total_list.by_id(str(int(music.id) % 10000)) and total_list.by_id(str(int(music.id) % 10000 + 10000)):
        # 如果sd和dx谱都存在的话
        vital_clue.append(f'既有SD谱面也有DX谱面')
    else:
        clue_list.append(f'{"不" if music.type == "SD" else ""}是 DX 谱面')
    if total_list.by_id(str(int(music.id) + 100000)):
        vital_clue.append(f'有宴谱') 

    if len(music.ds) == 5:
        vital_clue.append(f'的白谱谱师为{music.charts[4].charter}')
        clue_list.append(f'的 Re:Master 难度是 {music.level[4]}')
    else:
        clue_list.append(f'没有白谱')
    
    random_clue = vital_clue
    random_clue += random.sample(clue_list, 6 - len(vital_clue))
    random.shuffle(random_clue)
    random_clue.append(final_clue)
    return random_clue


@guess_clue.handle()
async def _(event: GroupMessageEvent, matcher: Matcher, args: Message = CommandArg()):
    if len(total_list.music_list) == 0:
        await matcher.finish("本插件还没有配置好static资源噢，请让bot主尽快到 https://github.com/apshuang/nonebot-plugin-guess-song 下载资源吧！")
    group_id = str(event.group_id)
    game_name = "clue"
    if check_game_disable(group_id, game_name):
        await matcher.finish(f"本群禁用了{game_alias_map[game_name]}游戏，请联系管理员使用“/开启猜歌 {game_alias_map[game_name]}”来开启游戏吧！")
    params = args.extract_plain_text().strip().split()
    await isplayingcheck(group_id, matcher)
    await clue_guess_handler(group_id, matcher, params)

@continuous_guess_clue.handle()
async def _(event: GroupMessageEvent, matcher: Matcher, args: Message = CommandArg()):
    if len(total_list.music_list) == 0:
        await matcher.finish("本插件还没有配置好static资源噢，请让bot主尽快到 https://github.com/apshuang/nonebot-plugin-guess-song 下载资源吧！")
    group_id = str(event.group_id)
    game_name = "clue"
    if check_game_disable(group_id, game_name):
        await matcher.finish(f"本群禁用了{game_alias_map[game_name]}游戏，请联系管理员使用“/开启猜歌 {game_alias_map[game_name]}”来开启游戏吧！")
    params = args.extract_plain_text().strip().split()
    await isplayingcheck(group_id, matcher)
    if not filter_random(total_list.music_list, params, 1):
        await matcher.finish(fault_tips, reply_message=True)
    await matcher.send('连续线索猜歌已开启，发送\"停止\"以结束')
    continuous_stop[group_id] = 1
    while continuous_stop.get(group_id):
        if gameplay_list.get(group_id) is None:
            await clue_guess_handler(group_id, matcher, params)
        if continuous_stop[group_id] > 3:
            continuous_stop.pop(group_id)
            await matcher.finish('没人猜了？ 那我下班了。')
        await asyncio.sleep(1)

async def clue_guess_handler(group_id, matcher: Matcher, args):
    if _ := filter_random(total_list.music_list, args, 1):
        random_music = _[0]
    else:
        await matcher.finish(fault_tips, reply_message=True)
    clues = await get_clues(random_music)
    gameplay_list[group_id] = {}
    gameplay_list[group_id]["clue"] = random_music
    
    await matcher.send("我将每隔8秒给你一些和这首歌相关的线索，直接输入歌曲的 id、标题、有效别名 都可以进行猜歌。", reply_message=True)
    await asyncio.sleep(5)
    for cycle in range(8):
        if group_id not in gameplay_list or not gameplay_list[group_id].get("clue"):
            break
        if gameplay_list[group_id].get("clue") != random_music:
            break

        if cycle < 5:
            await matcher.send(f'[线索 {cycle + 1}/8] 这首歌{clues[cycle]}')
            await asyncio.sleep(8)
        elif cycle < 7:
            # 最后俩线索太明显，多等一会
            await matcher.send(f'[线索 {cycle + 1}/8] 这首歌{clues[cycle]}')
            await asyncio.sleep(12)
        else:
            pic_path = music_cover_path / (get_cover_len5_id(random_music.id) + ".png")
            draw = await pic(pic_path)
            await matcher.send(
                MessageSegment.text('[线索 8/8] 这首歌封面的一部分是：\n') + 
                MessageSegment.image(image_to_base64(draw)) + 
                MessageSegment.text('答案将在30秒后揭晓')
                )
            for _ in range(30):
                await asyncio.sleep(1)
                if gameplay_list.get(group_id) is None or not gameplay_list[group_id].get("clue") or gameplay_list[group_id].get("clue") != random_music:
                    if continuous_stop.get(group_id):
                        continuous_stop[group_id] = 1
                    return
                
            gameplay_list.pop(group_id)
            reply_message = MessageSegment.text("很遗憾，你没有猜到答案，正确的答案是：\n") + song_txt(random_music)
            await matcher.send(reply_message)
            if continuous_stop.get(group_id):
                continuous_stop[group_id] += 1
    
    
async def clue_open_song_handler(matcher, song_name, group_id, user_id, ignore_tag):
    '''开歌处理函数'''
    clue_info = gameplay_list.get(group_id).get("clue")
    music_candidates = alias_dict.get(song_name)
    if music_candidates is None:
        if ignore_tag:
            return
        await matcher.finish("没有找到这样的乐曲。请输入正确的名称或别名", reply_message=True)
    
    if len(music_candidates) < 20:
        for music_index in music_candidates:
            music = total_list.music_list[music_index]
            if clue_info.id == music.id:
                gameplay_list.pop(group_id)
                record_game_success(user_id=user_id, group_id=group_id, game_type="clue")
                reply_message = MessageSegment.text("恭喜你猜对啦！答案就是：\n") + song_txt(music)
                await matcher.finish(Message(reply_message), reply_message=True)
    if not ignore_tag:        
        await matcher.finish("你猜的答案不对噢，再仔细听一下吧！", reply_message=True)
        

def clue_rank_message(group_id):
    top_clue = get_top_three(group_id, "clue")
    if top_clue:
        msg = "今天的前三名线索猜歌王：\n"
        for rank, (user_id, count) in enumerate(top_clue, 1):
            msg += f"{rank}. {MessageSegment.at(user_id)} 猜对了{count}首歌！\n"
        msg += "你们赢了……"
        return msg