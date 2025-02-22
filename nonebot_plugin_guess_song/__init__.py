from nonebot import get_plugin_config, get_bot
from nonebot import on_startswith, on_command, on_fullmatch, on_message
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Message, MessageSegment, GroupMessageEvent, Bot
from nonebot.params import Startswith
from nonebot.matcher import Matcher
from nonebot.plugin import PluginMetadata, require

from .libraries import *
from .config import *


scheduler = require('nonebot_plugin_apscheduler')
require("nonebot_plugin_localstore")

from nonebot_plugin_apscheduler import scheduler

__plugin_meta__ = PluginMetadata(
    name="maimai猜歌小游戏",
    description="音游猜歌游戏插件，提供开字母、听歌猜曲、谱面猜歌、猜曲绘、线索猜歌等游戏",
    usage="/猜歌帮助",
    type="application",
    config=Config,
    homepage="https://github.com/apshuang/nonebot-plugin-guess-song",
)


def is_now_playing_game(event: GroupMessageEvent) -> bool:
    return gameplay_list.get(str(event.group_id)) is not None

open_song = on_startswith(("开歌","猜歌"), priority=3, ignorecase=True, block=True, rule=is_now_playing_game)
open_song_without_prefix = on_message(rule=is_now_playing_game, priority=10)
stop_game = on_fullmatch(("不玩了", "不猜了"))
stop_game_force = on_fullmatch("强制停止")
stop_continuous = on_fullmatch('停止')
top_three = on_command('前三')
guess_random = on_command('随机猜歌')
continuous_guess_random = on_command('连续随机猜歌')
help_guess = on_command('猜歌帮助')
charter_names = on_command('查看谱师')
enable_guess_game = on_command('开启猜歌', priority=5, permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER)
disable_guess_game = on_command('关闭猜歌', priority=5, permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER)

@help_guess.handle()
async def _(matcher: Matcher):
    await matcher.finish(MessageSegment.image(to_bytes_io(guess_help_message)))

@charter_names.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    msglist = []
    for names in charterlist.values():
        msglist.append(', '.join(names))
    msglist.append('以上是目前已知的谱师名单，如有遗漏请联系管理员添加。')
    await send_forward_message(bot, event.group_id, bot.self_id, msglist)

@guess_random.handle()
async def _(event: GroupMessageEvent, matcher: Matcher, args: Message = CommandArg()):
    if len(total_list.music_list) == 0:
        await matcher.finish("本插件还没有配置好static资源噢，请让bot主尽快到 https://github.com/apshuang/nonebot-plugin-guess-song 下载资源吧！")
    group_id = str(event.group_id)
    game_name = "random"
    if check_game_disable(group_id, game_name):
        await matcher.finish(f"本群禁用了{game_alias_map[game_name]}游戏，请联系管理员使用“/开启猜歌 {game_alias_map[game_name]}”来开启游戏吧！")
    params = args.extract_plain_text().strip().split()
    await isplayingcheck(group_id, matcher)
    choice = random.randint(1, 3)
    if choice == 1:
        await guess_cover_handler(group_id, matcher, params)
    elif choice == 2:
        await clue_guess_handler(group_id, matcher, params)
    elif choice == 3:
        await listen_guess_handler(group_id, matcher, params)

@continuous_guess_random.handle()
async def _(event: GroupMessageEvent, matcher: Matcher, args: Message = CommandArg()):
    if len(total_list.music_list) == 0:
        await matcher.finish("本插件还没有配置好static资源噢，请让bot主尽快到 https://github.com/apshuang/nonebot-plugin-guess-song 下载资源吧！")
    group_id = str(event.group_id)
    game_name = "random"
    if check_game_disable(group_id, game_name):
        await matcher.finish(f"本群禁用了{game_alias_map[game_name]}游戏，请联系管理员使用“/开启猜歌 {game_alias_map[game_name]}”来开启游戏吧！")
    params = args.extract_plain_text().strip().split()
    await isplayingcheck(group_id, matcher)
    if not filter_random(total_list.music_list, params, 1):
        await matcher.finish(fault_tips, reply_message=True)
    await matcher.send('连续随机猜歌已开启，发送\"停止\"以结束')
    continuous_stop[group_id] = 1
    while continuous_stop.get(group_id):
        if gameplay_list.get(group_id) is None:
            choice = random.randint(1, 3)
            if choice == 1:
                await guess_cover_handler(group_id, matcher, params)
            elif choice == 2:
                await clue_guess_handler(group_id, matcher, params)
            elif choice == 3:
                await listen_guess_handler(group_id, matcher, params)
        if continuous_stop[group_id] > 3:
            continuous_stop.pop(group_id)
            await matcher.finish('没人猜了？ 那我下班了。')
        await asyncio.sleep(1)

async def open_song_dispatcher(matcher: Matcher, song_name, user_id, group_id, ignore_tag=False):
    if gameplay_list.get(group_id).get("open_character"):
        await character_open_song_handler(matcher, song_name, group_id, user_id, ignore_tag)
    elif gameplay_list.get(group_id).get("listen"):
        await listen_open_song_handler(matcher, song_name, group_id, user_id, ignore_tag)
    elif gameplay_list.get(group_id).get("cover"):
        await cover_open_song_handler(matcher, song_name, group_id, user_id, ignore_tag)
    elif gameplay_list.get(group_id).get("clue"):
        await clue_open_song_handler(matcher, song_name, group_id, user_id, ignore_tag)
    elif gameplay_list.get(group_id).get("chart"):
        await chart_open_song_handler(matcher, song_name, group_id, user_id, ignore_tag)

@open_song.handle()
async def open_song_handler(event: GroupMessageEvent, matcher: Matcher, start: str = Startswith()):
    song_name = event.get_plaintext().lower()[len(start):].strip()
    if song_name == "":
        await matcher.finish("无效的请求，请使用格式：开歌xxxx（xxxx 是歌曲名称）", reply_message=True)
    await open_song_dispatcher(matcher, song_name, event.user_id, str(event.group_id))
        
                    
@open_song_without_prefix.handle()
async def open_song_without_prefix_handler(event: GroupMessageEvent, matcher: Matcher):
    # 直接输入曲名也可以视作答题，但是答题错误的话不返回任何信息（防止正常聊天也被视作答题）
    song_name = event.get_plaintext().strip().lower()
    if song_name == "" or alias_dict.get(song_name) is None:
        return
    await open_song_dispatcher(matcher, song_name, event.user_id, str(event.group_id), True)


@stop_game_force.handle()
async def _(event: GroupMessageEvent, matcher: Matcher):
    # 中途停止的处理函数
    group_id = str(event.group_id)
    if gameplay_list.get(group_id):
        gameplay_list.pop(group_id)
    if continuous_stop.get(group_id):
        continuous_stop.pop(group_id)
    if groupID_params_map.get(group_id):
        groupID_params_map.pop(group_id)
    await matcher.finish("已强行停止当前游戏")
    

@stop_game.handle()
async def _(event: GroupMessageEvent, matcher: Matcher):
    # 中途停止的处理函数
    group_id = str(event.group_id)
    if gameplay_list.get(group_id) is not None:
        now_playing_game = list(gameplay_list.get(group_id).keys())[0]
        if now_playing_game == "open_character":
            message = open_character_message(group_id, early_stop = True)
            await matcher.finish(message)
        elif now_playing_game in ["listen", "cover", "clue"]:
            music = gameplay_list.get(group_id).get(now_playing_game)
            gameplay_list.pop(group_id)
            await matcher.finish(
                MessageSegment.text(f'很遗憾，你没有猜到答案，正确的答案是：\n') + song_txt(music) + MessageSegment.text('\n\n。。30秒都坚持不了吗')
                ,reply_message=True)
        elif now_playing_game == "chart":
            answer_clip_path = gameplay_list.get(group_id).get("chart")
            gameplay_list.pop(group_id)  # 需要先pop，不然的话发了答案之后还能猜
            random_music_id, start_time = split_id_from_path(answer_clip_path)
            is_remaster = False
            if int(random_music_id) > 500000:
                # 是白谱，需要找回原始music对象
                random_music_id = str(int(random_music_id) % 500000)
                is_remaster = True
            random_music = total_list.by_id(random_music_id)
            charts_save_list.append(answer_clip_path)  # 但是必须先把它保护住，否则有可能发到一半被删掉
            reply_message = MessageSegment.text("很遗憾，你没有猜到答案，正确的答案是：\n") + song_txt(random_music, is_remaster) + "\n对应的原片段如下："
            await matcher.send(reply_message, reply_message=True)
            if answer_clip_path in loading_clip_list:
                for i in range(31):
                    await asyncio.sleep(1)
                    if answer_clip_path not in loading_clip_list:
                        break
                    if i == 30:
                        await matcher.finish(f"答案文件可能坏掉了，这个谱的开始时间是{start_time}秒，如果感兴趣可以自己去搜索噢", reply_message=True)
            await matcher.send(MessageSegment.video(f"file://{answer_clip_path}"))
            os.remove(answer_clip_path)
            charts_save_list.remove(answer_clip_path)  # 发完了就可以解除保护了
            

@stop_continuous.handle()
async def _(event: GroupMessageEvent, matcher: Matcher):
    group_id = str(event.group_id)
    if groupID_params_map.get(group_id):
        groupID_params_map.pop(group_id)
    if continuous_stop.get(group_id):
        continuous_stop.pop(group_id)
        await matcher.finish('已停止，坚持把最后一首歌猜完吧！')

def add_credit_message(group_id):
    record = {}
    gid = str(group_id)
    game_data = load_game_data_json(gid)
    user_info = load_data(user_info_path)    # 这里主要是给用户加分，可以按需使用
    for game_name, data in game_data[gid]['rank'].items():
        for user_id, point in data.items():
            try:
                user_info[user_id]['credit'] += point // point_per_credit_dict[game_name]
                record.setdefault(user_id, [0, 0])
                record[user_id][0] += point
                record[user_id][1] += point // point_per_credit_dict[game_name]
            except:
                pass
    save_game_data(user_info, user_info_path)
    sorted_record = sorted(record.items(), key=lambda x: (x[1][1], x[1][0]), reverse=True)
    if sorted_record:
        msg = f'今日加分记录：\n'
        for rank, (user_id, count) in enumerate(sorted_record, 1):
            msg += f"{rank}. {MessageSegment.at(user_id)} 答对{count[0]}题，加{count[1]}分！\n"
        msg += "便宜你们了。。"
        return msg

async def send_top_three(bot, group_id, isaddcredit = False, is_force = False):
    sender_id = bot.self_id
    char_msg = open_character_rank_message(group_id)
    listen_msg = listen_rank_message(group_id)
    cover_msg = cover_rank_message(group_id)
    clue_msg = clue_rank_message(group_id)
    chart_msg = chart_rank_message(group_id)
    
    origin_messages = [char_msg, listen_msg, cover_msg, clue_msg, chart_msg]
    if isaddcredit:
        origin_messages.append(add_credit_message(group_id))
    if is_force:
        empty_tag = True
        for msg in origin_messages:
            if msg is not None:
                empty_tag = False
        if empty_tag:
            await bot.send_group_msg(group_id=group_id, message=Message(MessageSegment.text("本群还没有猜歌排名数据噢！快来玩一下猜歌游戏吧！")))
            return
    await send_forward_message(bot, group_id, sender_id, origin_messages)
    
    
@enable_guess_game.handle()
@disable_guess_game.handle()
async def _(matcher: Matcher, event: GroupMessageEvent, arg: Message = CommandArg()):
    gid = str(event.group_id)
    arg = arg.extract_plain_text().strip().lower()
    enable_sign = True
    if type(matcher) is enable_guess_game:
        enable_sign = True
    elif type(matcher) is disable_guess_game:
        enable_sign = False
    else:
        raise ValueError('matcher type error')
    
    global global_game_data
    global_game_data = load_game_data_json(gid)
    if arg == "all" or arg == "全部":
        for key in global_game_data[gid]['game_enable'].keys():
            global_game_data[gid]['game_enable'][key] = enable_sign
        msg = f'已将本群的全部猜歌游戏全部设为{"开启" if enable_sign else "禁用"}'
    elif game_alias_map.get(arg):
        global_game_data[gid]["game_enable"][arg] = enable_sign
        msg = f'已将本群的{game_alias_map.get(arg)}设为{"开启" if enable_sign else "禁用"}'
    elif game_alias_map_reverse.get(arg):
        global_game_data[gid]["game_enable"][game_alias_map_reverse[arg]] = enable_sign
        msg = f'已将本群的{arg}设为{"开启" if enable_sign else "关闭"}'
    else:
        msg = '您的输入有误，请输入游戏名（比如开字母、谱面猜歌、全部）或其英文（比如listen、cover、all）来进行开启或禁用猜歌游戏'
    save_game_data(global_game_data, game_data_path)
    print(global_game_data)
    await matcher.finish(msg)

@top_three.handle()
async def top_three_handler(event: GroupMessageEvent, matcher: Matcher, bot: Bot):
    await send_top_three(bot, event.group_id, is_force=True)

@scheduler.scheduled_job('cron', hour=15, minute=00)
async def _():
    bot: Bot = get_bot()
    group_list = await bot.call_api("get_group_list")
    for group_info in group_list:
        group_id = str(group_info.get("group_id"))
        await send_top_three(bot, group_id)


@scheduler.scheduled_job('cron', hour=23, minute=57)
async def send_top_three_schedule():
    bot: Bot = get_bot()
    group_list = await bot.call_api("get_group_list")
    for group_info in group_list:
        group_id = str(group_info.get("group_id"))
        
        # 如果不需要给用户加分（仅展示答对题数与排名），可以将这里的isaddcredit设为False
        await send_top_three(bot, group_id, isaddcredit=True)


@scheduler.scheduled_job('cron', hour=00, minute=00)
async def reset_game_data():
    data = load_data(game_data_path)
    for gid in data.keys():
        data[gid]['rank'] = {"listen": {}, "open_character": {},"cover": {}, "clue": {}, "chart": {}}
    save_game_data(data, game_data_path)
