import asyncio
from re import M
from typing import Tuple
from datetime import datetime

from .utils import check_game_disable, isplayingcheck, filter_random, record_game_success, fault_tips, song_txt
from .music_model import gameplay_list, game_alias_map, alias_dict, total_list, Music, continuous_stop
from ..config import levelList

from nonebot import on_command
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment, Message
from nonebot.params import CommandArg


# 超参数配置
MAX_GUESSES_PER_USER = 10  # 单个玩家最多猜测次数
MAX_TOTAL_GUESSES = 30  # 所有玩家总计最多猜测次数
TIMEOUT_MINUTES = 3  # 超时时间（分钟）

guess_maidle = on_command("maidle", aliases={"开maidle", "猜maidle"}, priority=5)
continuous_guess_maidle = on_command("连续maidle", aliases={"连续开maidle", "连续猜maidle"}, priority=5)


# 版本列表（去掉"maimai でらっくす"之后的PLUS版本）
VERSION_LIST = [
    "maimai", "maimai PLUS",
    "maimai GreeN", "maimai GreeN PLUS",
    "maimai ORANGE", "maimai ORANGE PLUS",
    "maimai PiNK", "maimai PiNK PLUS",
    "maimai MURASAKi", "maimai MURASAKi PLUS",
    "maimai MiLK", "MiLK PLUS",
    "maimai FiNALE",
    "maimai でらっくす",
    "maimai でらっくす Splash",
    "maimai でらっくす UNiVERSE",
    "maimai でらっくす FESTiVAL",
    "maimai でらっくす BUDDiES",
    "maimai でらっくす PRiSM",
    "maimai でらっくす PRiSM PLUS"
]


def compare_version(guess_version: str, answer_version: str) -> Tuple[str, bool]:
    """比较版本号，返回(状态, 是否接近)"""
    try:
        guess_idx = VERSION_LIST.index(guess_version)
        answer_idx = VERSION_LIST.index(answer_version)
    except ValueError:
        raise ValueError(f"版本号错误：{guess_version} 或 {answer_version} 没有配置")  
          
    if guess_idx == answer_idx:
        return ("correct", False)
    diff = abs(guess_idx - answer_idx)
    direction = "higher" if answer_idx > guess_idx else "lower"
    return (direction, diff == 1)


def compare_level(guess_level: str, answer_level: str) -> Tuple[str, bool]:
    """比较等级，返回(状态, 是否接近)"""
    try:
        guess_idx = levelList.index(guess_level)
        answer_idx = levelList.index(answer_level)
    except ValueError:
        raise Exception(f"等级错误：{guess_level} 或 {answer_level} 没有配置")
    
    if guess_idx == answer_idx:
        return ("correct", False)
    diff = abs(guess_idx - answer_idx)
    direction = "higher" if answer_idx > guess_idx else "lower"
    return (direction, diff == 1)


def compare_bpm(guess_bpm: float, answer_bpm: float) -> Tuple[str, bool]:
    """比较BPM，返回(状态, 是否接近)"""
    diff = abs(guess_bpm - answer_bpm)
    if diff < 0.1:
        return ("correct", False)
    direction = "higher" if answer_bpm > guess_bpm else "lower"
    return (direction, diff <= 10.0)


def compare_string(guess: str, answer: str) -> Tuple[str, bool]:
    """比较字符串，返回(状态, 是否接近)"""
    return ("correct", False) if guess.lower() == answer.lower() else ("incorrect", False)


def format_feedback(status: str, is_close: bool, label: str, value: str) -> str:
    """格式化反馈信息：symbol label：信息 方向"""
    if status == "correct":
        return f"✅ {label}：{value}"
    elif status == "incorrect":
        return f"❌ {label}：{value}"
    
    # 方向用emoji
    direction_emoji = "⬆️" if status == "higher" else "⬇️"
    symbol = "🟡" if is_close else "❌"
    return f"{symbol} {label}：{value} {direction_emoji}"


def generate_feedback(guess_music: Music, answer_music: Music, current_guess_count: int) -> tuple[int, str]:
    """根据猜测音乐和答案音乐生成反馈消息，返回猜测次数和反馈消息"""
    guess_count = 0
    lines = [f"第{current_guess_count}/{MAX_TOTAL_GUESSES}次猜测："]

    # 歌名
    status, _ = compare_string(guess_music.title, answer_music.title)
    lines.append(format_feedback(status, False, "歌名", guess_music.title))
    guess_count += status == "correct"

    # 分类
    status, _ = compare_string(guess_music.genre, answer_music.genre)
    lines.append(format_feedback(status, False, "分类", guess_music.genre))
    guess_count += status == "correct"

    # 曲师
    status, _ = compare_string(guess_music.artist, answer_music.artist)
    lines.append(format_feedback(status, False, "曲师", guess_music.artist))
    guess_count += status == "correct"
    
    # 版本
    status, is_close = compare_version(guess_music.version, answer_music.version)
    lines.append(format_feedback(status, is_close, "版本", guess_music.version))
    guess_count += status == "correct"

    # 类型（SD/DX）
    status, _ = compare_string(guess_music.type, answer_music.type)
    lines.append(format_feedback(status, False, "类型", guess_music.type))
    guess_count += status == "correct"

    # BPM
    status, is_close = compare_bpm(guess_music.bpm, answer_music.bpm)
    lines.append(format_feedback(status, is_close, "BPM", str(int(guess_music.bpm))))
    guess_count += status == "correct"

    # 紫谱等级
    if len(guess_music.level) >= 4 and len(answer_music.level) >= 4:
        status, is_close = compare_level(guess_music.level[3], answer_music.level[3])
        lines.append(format_feedback(status, is_close, "紫谱等级", guess_music.level[3]))
        guess_count += status == "correct"

    # 紫谱谱师
    if len(guess_music.charts) >= 4 and len(answer_music.charts) >= 4:
        status, _ = compare_string(guess_music.charts[3].charter, answer_music.charts[3].charter)
        lines.append(format_feedback(status, False, "紫谱谱师", guess_music.charts[3].charter))
        guess_count += status == "correct"

    # 白谱等级（如果有）
    if len(guess_music.level) >= 5 and len(answer_music.level) >= 5:
        status, is_close = compare_level(guess_music.level[4], answer_music.level[4])
        lines.append(format_feedback(status, is_close, "白谱等级", guess_music.level[4]))
        guess_count += status == "correct"
    
    return guess_count, "\n".join(lines)


def generate_statistics(maidle_info: dict, is_success: bool = False, winner_user_id: int | None = None) -> list[MessageSegment]:
    """生成游戏统计信息"""
    user_guesses = maidle_info.get("user_guesses", {})
    best_guess = maidle_info.get("best_guess", (None, 0))
    best_progress = maidle_info.get("best_progress", (None, 0))
    total_guesses = maidle_info.get("total_guesses", 0)
    start_time = maidle_info.get("start_time")
    winner_time = maidle_info.get("winner_time")
    winner_user_id = maidle_info.get("winner_user_id")
    
    if not user_guesses:
        return [MessageSegment.text("没有玩家参与游戏")]
    
    # 参与人数
    participant_count = len(user_guesses)
    
    # 游戏时长
    if start_time:
        end_time = winner_time if winner_time else datetime.now()
        duration = end_time - start_time
        duration_str = f"{int(duration.total_seconds() // 60)}分{int(duration.total_seconds() % 60)}秒"
    else:
        duration_str = "未知"
    
    stats = [
        MessageSegment.text(f"📊 游戏统计：\n"),
        MessageSegment.text(f"总参与人数：{participant_count}人\n"),
        MessageSegment.text(f"总猜测次数：{total_guesses}次\n"),
        MessageSegment.text(f"游戏时长：{duration_str}\n"),
    ]
    
    # 最活跃玩家（猜测次数最多的玩家）
    if user_guesses:
        top_guesser = max(user_guesses.items(), key=lambda x: x[1])
        top_user_id, top_count = top_guesser
        stats.extend([MessageSegment.text("💪 最活跃玩家："), MessageSegment.at(int(top_user_id)), MessageSegment.text(f"（{top_count}次）\n")])
    
    # 猜对最多条目的玩家（记录没猜对时的最大猜对条目数）
    if best_guess[0] is not None:
        best_guess_user_id, best_guess_count = best_guess
        if best_guess_count > 0:
            stats.extend([MessageSegment.text("✨ 最接近答案："), MessageSegment.at(int(best_guess_user_id)), MessageSegment.text(f"（猜对{best_guess_count}条）\n")])
     
    # 进步最快玩家（从第一次到最后一次，猜对条目数增长最多的）
    if best_progress[0] is not None:
        best_progress_user_id, best_progress_count = best_progress
        if best_progress_count > 0:
            stats.extend([MessageSegment.text("🚀 新猜对最多："), MessageSegment.at(int(best_progress_user_id)), MessageSegment.text(f"（+{best_progress_count}条）\n")])
    
    # 猜对答案玩家
    if winner_user_id is not None:
        stats.extend([MessageSegment.text("👑 猜对答案玩家："), MessageSegment.at(int(winner_user_id))])
    return stats


@guess_maidle.handle()
async def _(event: GroupMessageEvent, matcher: Matcher, args: Message = CommandArg()):
    """开始 maidle 游戏"""
    if len(total_list.music_list) == 0:
        await matcher.finish("本插件还没有配置好static资源噢，请让bot主尽快到 https://github.com/apshuang/nonebot-plugin-guess-song 下载资源吧！")
    
    group_id = str(event.group_id)
    game_name = "maidle"
    if check_game_disable(group_id, game_name):
        await matcher.finish(f"本群禁用了{game_alias_map.get(game_name, 'maidle')}游戏，请联系管理员使用\"/开启猜歌 {game_alias_map.get(game_name, 'maidle')}\"来开启游戏吧！")
    params = args.extract_plain_text().strip().split()
    await isplayingcheck(group_id, matcher)
    await maidle_guess_handler(group_id, matcher, params)


async def maidle_guess_handler(group_id, matcher: Matcher, args):
    """开始 maidle 游戏"""
    if not (random_music := filter_random(total_list.music_list, args, 1)):
        await matcher.finish(fault_tips, reply_message=True)
    
    answer_music = random_music[0]
    start_time = datetime.now()
    
    # 初始化游戏状态
    gameplay_list[group_id] = {}
    gameplay_list[group_id]["maidle"] = {
        "answer": answer_music,
        "user_guesses": {},
        "best_guess": (None, 0),
        "best_progress": (None, 0),
        "total_guesses": 0,
        "start_time": start_time,
        "winner_guesser_id": None,
        "params": args
    }
    
    message = (
        "[maidle 猜歌游戏]\n"
        "游戏已开始！请猜测一首歌曲。\n"
        "我会告诉你哪些属性是正确的（✅），哪些是错误的（❌），以及哪些是接近的（🟡）。\n"
        f"单个玩家最多猜测 {MAX_GUESSES_PER_USER} 次，所有玩家总计最多猜测 {MAX_TOTAL_GUESSES} 次。\n"
        f"游戏将在 {TIMEOUT_MINUTES} 分钟后自动结束。\n"
    )
    if args:
        message += f"本次游戏范围：{', '.join(args)}\n"
    message += "\n发送 \"开歌xxx\" 或直接输入歌曲名称来猜测！"
    await matcher.send(message)

    for _ in range(TIMEOUT_MINUTES * 60):
        await asyncio.sleep(1)
        if gameplay_list.get(group_id) is None or not gameplay_list[group_id].get("maidle") or gameplay_list[group_id].get("maidle").get("answer") != answer_music:
            if continuous_stop.get(group_id):
                continuous_stop[group_id] = 1
            return
    
    # 超时结束
    stats = generate_statistics(gameplay_list[group_id]["maidle"], is_success=False)
    gameplay_list.pop(group_id)
    reply_message = [MessageSegment.text("很遗憾，你没有猜到答案，正确的答案是：\n")]
    reply_message.extend(song_txt(answer_music))
    if stats:
        reply_message.append(MessageSegment.text("\n\n"))
        reply_message.extend(stats)
    await matcher.send(Message(reply_message))
    if continuous_stop.get(group_id):
        continuous_stop[group_id] += 1


@continuous_guess_maidle.handle()
async def _(event: GroupMessageEvent, matcher: Matcher, args: Message = CommandArg()):
    group_id = str(event.group_id)
    game_name = "maidle"
    if check_game_disable(group_id, game_name):
        await matcher.finish(f"本群禁用了{game_alias_map[game_name]}游戏，请联系管理员使用“/开启猜歌 {game_alias_map[game_name]}”来开启游戏吧！")
    params = args.extract_plain_text().strip().split()
    await isplayingcheck(group_id, matcher)
    if not filter_random(total_list.music_list, params, 1):
        await matcher.finish(fault_tips, reply_message=True)
    await matcher.send('连续maidle游戏已开启，发送\"停止\"以结束')
    continuous_stop[group_id] = 1
    while continuous_stop.get(group_id):
        if gameplay_list.get(group_id) is None:
            await maidle_guess_handler(group_id, matcher, params)
        if continuous_stop[group_id] > 3:
            continuous_stop.pop(group_id)
            await matcher.finish('没人猜了？ 那我下班了。')
        await asyncio.sleep(1)


async def maidle_open_song_handler(matcher: Matcher, song_name: str, group_id: str, user_id: int, ignore_tag: bool):
    """处理 maidle 游戏的猜测"""
    maidle_info = gameplay_list[group_id]["maidle"]
    answer_music = maidle_info["answer"]
    user_guesses = maidle_info["user_guesses"]
    user_guess_count = user_guesses.get(str(user_id), 0) + 1  # 当前玩家猜测次数，包括本次
    best_guess_count = maidle_info["best_guess"][1]
    best_progress_count = maidle_info["best_progress"][1]
    total_guesses = maidle_info["total_guesses"] + 1
    
    # 查找猜测的歌曲
    music_candidates = alias_dict.get(song_name)
    if music_candidates is None:
        # 如果没有找到对应的歌曲，且ignore_tag为True，说明用户可能只是在聊天，不是猜歌，直接忽略
        if ignore_tag:
            return
        await matcher.finish("没有找到这样的乐曲。请输入正确的名称或别名", reply_message=True)
    else:
        # 如果确实在说某一首歌，就视为在猜歌，那么检查猜测次数限制，如果超过则提醒
        if user_guess_count > MAX_GUESSES_PER_USER:
            await matcher.finish(f"您已达到单个玩家的最大猜测次数（{MAX_GUESSES_PER_USER}次），请看看其他玩家的表现吧！", reply_message=True)
        
    if len(music_candidates) >= 20:
        if ignore_tag:
            return
        await matcher.finish("匹配到的歌曲太多，请使用更精确的名称", reply_message=True)
    
    # 检查是否猜对
    guessed_correctly = False
    best_correct_count = 0
    guess_music = None
    
    for music_index in music_candidates:
        music = total_list.music_list[music_index]
        if music.id == answer_music.id:
            guessed_correctly = True
            guess_music = music
            break
        else:
            correct_count = generate_feedback(music, answer_music, total_guesses)[0]
            if correct_count > best_correct_count:
                best_correct_count = correct_count
                guess_music = music
    
    if not guess_music:
        guess_music = total_list.music_list[music_candidates[0]]
    
    # 如果猜对了
    if guessed_correctly:
        maidle_info["winner_time"] = datetime.now()
        maidle_info["winner_user_id"] = user_id
        
        # 记录success（猜对歌曲的人）
        record_game_success(user_id=user_id, group_id=int(group_id), game_type="maidle")
        gameplay_list.pop(group_id)
        stats = generate_statistics(maidle_info, is_success=True, winner_user_id=user_id)
        reply_message = [MessageSegment.text("🎉 恭喜你猜对啦！答案就是：\n")]
        reply_message.extend(song_txt(answer_music))
        if stats:
            reply_message.append(MessageSegment.text("\n\n"))
            reply_message.extend(stats)
        await matcher.finish(Message(reply_message), reply_message=True)
    
    # 如果没猜对，则更新猜测次数
    user_guesses[str(user_id)] = user_guess_count
    maidle_info["total_guesses"] = total_guesses
    if best_correct_count > best_guess_count:
        maidle_info["best_guess"] = (user_id, best_correct_count)
    progress_count = best_correct_count - best_guess_count
    if progress_count > best_progress_count:
        maidle_info["best_progress"] = (user_id, progress_count)
    
    # 达到总最大猜测次数，则early stop
    if total_guesses >= MAX_TOTAL_GUESSES:
        gameplay_list.pop(group_id)
        stats = generate_statistics(maidle_info, is_success=False)
        reply_message = [MessageSegment.text(f"已达到总猜测次数上限 {MAX_TOTAL_GUESSES} 次，很遗憾，你没有猜到答案！\n正确答案是：\n")]
        reply_message.extend(song_txt(answer_music))
        if stats:
            reply_message.append(MessageSegment.text("\n\n"))
            reply_message.extend(stats)
        await matcher.finish(Message(reply_message), reply_message=True)
    
    _, feedback_message = generate_feedback(guess_music, answer_music, total_guesses)
    await matcher.finish(Message(MessageSegment.text(feedback_message)), reply_message=True)


def maidle_rank_message(group_id: str):
    """生成 maidle 游戏的排行榜消息"""
    from .utils import get_top_three
    top_maidle = get_top_three(int(group_id), "maidle")
    if top_maidle:
        msg = "今日的前三名 maidle 高手：\n"
        for rank, (user_id, count) in enumerate(top_maidle, 1):
            msg += f"{rank}. {MessageSegment.at(user_id)} 猜对了{count}首歌！\n"
        msg += "太强了！"
        return msg
    return None
