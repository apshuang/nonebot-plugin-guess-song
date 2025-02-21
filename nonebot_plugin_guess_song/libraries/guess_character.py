import random

from .utils import *
from .music_model import gameplay_list, game_alias_map, filter_list, alias_dict, total_list

from nonebot import on_command, on_startswith
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.params import Startswith, CommandArg


guess_character_request = on_command("开字母", aliases = {"猜字母"})
guess_open = on_startswith("开", priority=5)


def open_character_message(group_id, first = False, early_stop = False):

    character_info = gameplay_list.get(group_id).get("open_character")
    song_info_list = character_info.get("info")
    guessed_character = character_info.get("guessed")
    params = character_info.get("params")

    message = "[猜你字母bot 开字母]\n"
    if len(params):
        message += f"本次开字母范围：{', '.join(params)}\n"
    total_success = 0

    # 展示各歌曲的开字母情况
    for i in range(len(song_info_list)):
        if song_info_list[i].get("state"):
            message += f"✅{i+1}. {song_info_list[i].get('title')}\n"
            total_success += 1
        elif early_stop:
            message += f"❌{i+1}. {song_info_list[i].get('title')}\n"
        else:
            message += f"❓{i+1}. {song_info_list[i].get('guessed')}\n"

    message += (
        f"已开字符：{', '.join(guessed_character)}\n"
    )

    if total_success == len(song_info_list):
        start_time = character_info.get("start_time")
        current_time = datetime.now()
        time_diff = current_time - start_time
        total_seconds = int(time_diff.total_seconds())
        message += f"全部猜对啦！本次开字母用时{total_seconds}秒\n"
        gameplay_list.pop(group_id)

    if early_stop:
        message += f"本次开字母只猜对了{total_success}首歌，要再接再厉哦！本次开字母结束\n"
        gameplay_list.pop(group_id)

    if first:
        message += (
            "发送 “开x” 揭开对应的字母（或字符）\n"
            "发送 “开歌xxx”，来提交您认为在答案中的曲目（无需带序号）\n"
            "发送 “不玩了” 退出开字母并公布答案"
        )

    return message


def open_character_reply_message(success_guess):
    message = ""
    if len(success_guess) == 0:
        message += "本次没有猜对任何曲目哦。"
    else:
        message += "你猜对了"
        for i in range(len(success_guess)):
            message += success_guess[i]
            if i != len(success_guess)-1:
                message += ", "
    message += "\n"
    return MessageSegment("text", {"text": message})


def open_character_rank_message(group_id):
    top_open_character = get_top_three(group_id, "open_character")
    if top_open_character:
        msg = "今天的前三名开字母高手：\n"
        for rank, (user_id, count) in enumerate(top_open_character, 1):
            msg += f"{rank}. {MessageSegment.at(user_id)} 开出了{count}首歌！\n"
        msg += "一堆maip。。。"
        return msg


@guess_character_request.handle()
async def guess_request_handler(matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()):
    # 启动游戏
    if len(total_list.music_list) == 0:
        await matcher.finish("本插件还没有配置好static资源噢，请让bot主尽快到 https://github.com/apshuang/nonebot-plugin-guess-song 下载资源吧！")
    group_id = str(event.group_id)
    game_name = "open_character"
    if check_game_disable(group_id, game_name):
        await matcher.finish(f"本群禁用了{game_alias_map[game_name]}游戏，请联系管理员使用“/开启猜歌 {game_alias_map[game_name]}”来开启游戏吧！")
    params = args.extract_plain_text().strip().split()
    await isplayingcheck(group_id, matcher)
    if not (random_music := filter_random(filter_list, params, 10)):
        await matcher.finish(fault_tips, reply_message=True)
    start_time = datetime.now()
    info_list = []
    for music in random_music:
        guessed = ''.join(['?' if char != ' ' else ' ' for char in music.title])
        info_list.append({"title": music.title, "guessed": guessed, "state": False})
    gameplay_list[group_id] = {}
    gameplay_list[group_id]["open_character"] = {"info": info_list, "guessed": [], "start_time": start_time, "params": params}
    await matcher.finish(open_character_message(group_id, first = True))
        
        
@guess_open.handle()
async def guess_open_handler(matcher: Matcher, event: GroupMessageEvent, start: str = Startswith()):
    # 开单个字母
    group_id = str(event.group_id)
    if gameplay_list.get(group_id) and gameplay_list.get(group_id).get("open_character") is not None:
        character_info = gameplay_list.get(group_id).get("open_character")
        character = event.get_plaintext().lower()[len(start):].strip()
        if len(character) != 1:
            return 
        if character != "":
            character = character.lower()
            if character_info.get("guessed").count(character) != 0:
                await matcher.finish("这个字母已经开过了哦，换一个字母吧", reply_message=True)
            character_info.get("guessed").append(character)
            for music in character_info.get("info"):
                title = music.get("title")
                guessed = list(music.get("guessed"))
                for i in range(len(title)):
                    if title[i].lower() == character:
                        guessed[i] = title[i]
                music["title"] = title
                music["guessed"] = ''.join(guessed)

            await matcher.finish(open_character_message(group_id))
        else:
            await matcher.finish("无效指令，请使用格式：开x（x只能是一个字符）", reply_message=True)


async def character_open_song_handler(matcher, song_name, group_id, user_id, ignore_tag):
    # 开歌的处理函数
    character_info = gameplay_list.get(group_id).get("open_character")
    music_candidates = alias_dict.get(song_name)
    if music_candidates is None:
        if ignore_tag:
            return
        await matcher.finish("没有找到这样的乐曲。请输入正确的名称或别名")
    
    success_guess = []
    if len(music_candidates) < 20:
        for music_index in music_candidates:
            music = total_list.music_list[music_index]
            for info in character_info.get('info'):
                if info.get('title') == music.title and info.get("state") == False:
                    blindly_guess_check = True
                    for char in info['guessed']:
                        if char != ' ' and char != '?':
                            blindly_guess_check = False
                            break
                    if blindly_guess_check:
                        # 如果盲狙中了，就随机发送“这么难他都会”的图
                        probability = random.random()
                        if probability < 0.4:
                            try:
                                pic_path: Path = game_pic_path / "so_hard.jpg"
                                await matcher.send(MessageSegment.image(f"file://{pic_path}"))
                            except:
                                await matcher.send("这么难他都会")
                    success_guess.append(music.title)
                    info['guessed'] = music.title
                    info['state'] = True
                    record_game_success(user_id=user_id, group_id=group_id, game_type="open_character")
    if len(success_guess) == 0 and ignore_tag:
        return
    message = open_character_reply_message(success_guess)
    message += open_character_message(group_id)
    await matcher.finish(message, reply_message=True)
    

