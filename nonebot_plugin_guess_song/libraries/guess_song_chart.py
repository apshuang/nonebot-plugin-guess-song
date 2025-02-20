import re
import copy
import random
import shutil
import asyncio
import subprocess
from moviepy.editor import VideoFileClip

from .utils import *
from .music_model import gameplay_list, game_alias_map, alias_dict, total_list, continuous_stop

from nonebot import on_fullmatch, on_command
from nonebot.plugin import require
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent

scheduler = require('nonebot_plugin_apscheduler')

from nonebot_plugin_apscheduler import scheduler

config = get_plugin_config(Config)

id_mp3_file_map = {}
id_mp4_file_map = {}
id_music_map = {}
groupID_params_map: Dict[int, str] = {}  # 这个map只在带参数的连续谱面猜歌下需要使用
chart_total_list: List[Music] = []  # 为谱面猜歌特制的total_list，包含紫白谱的music（两份），紫谱music去掉白谱的内容（定数等），白谱music去掉紫谱内容并顶到紫谱位置
loading_clip_list = []
groupID_folder2delete_timestamp_list: List = {}  # 在猜完之后需要删除参数文件夹，所以需记录下来（如果直接删除可能会导致race condition）
CLIP_DURATION = 30
GUESS_TIME = 90
PRELOAD_CHECK_TIME = 40  # 这个时间请根据服务器性能来设置，建议设置为制作一套谱面视频的时间+10秒左右
PRELOAD_CNT = 10
PARAM_PRELOAD_CHECK_TIME = 35
PARAM_PRELOAD_CNT = 3
TIME_TO_DELETE = 120

general_charts_pool = []
charts_save_list = []  # 用于存住当前正在游玩的answer文件，防止自检时删掉（因为它的question已经被删掉了，所以他可能会被当成单身谱面而被删掉）
param_charts_pool: Dict[str, List] = {}

guess_chart = on_command("看谱猜歌", aliases={"谱面猜歌"}, priority=5)    
continuous_guess_chart = on_command('连续谱面猜歌')
check_chart_file_completeness = on_command("检查谱面完整性", permission=SUPERUSER)

def random_video_clip(input_path, duration, music_id, output_folder):
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"输入文件不存在: {input_path}")
    os.makedirs(output_folder, exist_ok=True)
    
    with VideoFileClip(input_path) as video:
        video_duration = video.duration  # 视频总时长
        if duration > video_duration - 15:
            raise ValueError(f"截取时长不能超过视频总时长减去{15 + duration}秒")

        # 前5秒是片头，会露出曲名，后10秒是片尾，只会有无用的all perfect画面
        start_time = random.uniform(5, video_duration - duration - 10)
        # 需要注意，output_folder需要为绝对路径，才能准确地找到对应的文件
        output_path = os.path.join(output_folder, f"{music_id}_{int(start_time)}_clip.mp4")
        if os.path.isfile(output_path):
            raise Exception(f"生成了重复的文件")
        
        end_time = start_time + duration
        clip = video.subclip(start_time, end_time)
        clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
    return start_time, output_path


async def make_answer_video(video_file, audio_file, music_id, output_folder, start_time, duration):
    if not os.path.exists(video_file):
        print(f"Error: Video file '{video_file}' does not exist.")
        return
    if not os.path.exists(audio_file):
        print(f"Error: Audio file '{audio_file}' does not exist.")
        return

    os.makedirs(output_folder, exist_ok=True)
    answer_file = os.path.join(output_folder, f"{music_id}_answer.mp4")
    answer_clip_path = os.path.join(output_folder, f"{music_id}_{int(start_time)}_answer_clip.mp4")
    
    loading_clip_list.append(answer_clip_path)  # 保护一下（防止还没准备完毕就被发出了）
    
    # 使用异步线程来执行ffmpeg命令
    await asyncio.to_thread(run_ffmpeg, video_file, audio_file, answer_file)
    # 使用异步线程来处理视频
    await asyncio.to_thread(process_video, answer_file, answer_clip_path, start_time, duration)

    # 删除文件（可以保留同步操作）
    os.remove(answer_file)  # 删掉完整的答案文件（只发送前面猜的片段）
    loading_clip_list.remove(answer_clip_path)  # 解除保护

    return answer_clip_path


# 在后台线程中运行ffmpeg命令
def run_ffmpeg(video_file, audio_file, answer_file):
    command = [
        "ffmpeg",
        "-i", video_file,
        "-i", audio_file,
        "-c:v", "copy",   # Copy the video stream without re-encoding
        "-c:a", "aac",    # Encode the audio stream using AAC
        "-strict", "experimental",  # Allow experimental features
        "-map", "0:v:0",  # Use the video stream from the first input
        "-map", "1:a:0",  # Use the audio stream from the second input
        answer_file
    ]
    try:
        print("Merging video and audio...")
        subprocess.run(command, check=True)  # 合成视频文件
        print(f"Merging completed. File saved as '{answer_file}'.")
    except subprocess.CalledProcessError as e:
        print(f"Error during merging: {e}")
    except Exception as ex:
        print(f"An unexpected error occurred: {ex}")


def process_video(answer_file, output_path, start_time, duration):
    with VideoFileClip(answer_file) as video:
        video_duration = video.duration  # 视频总时长
        if duration > video_duration - 5:
            raise ValueError(f"截取时长不能超过视频总时长减去{5 + duration}秒")
        end_time = start_time + duration
        clip = video.subclip(start_time, end_time)
        clip.write_videofile(output_path, codec="libx264", audio_codec="aac")



def chart_rank_message(group_id):
    top_chart = get_top_three(group_id, "chart")
    if top_chart:
        msg = "今天的前三名谱面猜歌王：\n"
        for rank, (user_id, count) in enumerate(top_chart, 1):
            msg += f"{rank}. {MessageSegment.at(user_id)} 猜对了{count}首歌！\n"
        msg += "记忆大神啊。。。"
        return msg


async def chart_open_song_handler(matcher, song_name, group_id, user_id, ignore_tag):
    '''开歌处理函数'''
    answer_clip_path = gameplay_list[group_id].get("chart")
    
    random_music_id, start_time = split_id_from_path(answer_clip_path)
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
    
    if len(music_candidates) < 20:
        for music_index in music_candidates:
            music = total_list.music_list[music_index]
            if random_music.id == music.id:
                record_game_success(user_id=user_id, group_id=group_id, game_type="chart")
                gameplay_list.pop(group_id)  # 需要先pop，不然的话发了答案之后还能猜
                charts_save_list.append(answer_clip_path)  # 但是必须先把它保护住，否则有可能发到一半被删掉
                reply_message = MessageSegment.text("恭喜你猜对啦！答案就是：\n") + song_txt(random_music, is_remaster) + "\n对应的原片段如下："
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
                return
    if not ignore_tag:        
        await matcher.finish("你猜的答案不对噢，再仔细看一下吧！", reply_message=True)


@guess_chart.handle()
async def _(event: GroupMessageEvent, matcher: Matcher, args: Message = CommandArg()):
    if len(chart_total_list) == 0:
        await matcher.finish("文件夹没有下载任何谱面视频资源，请让bot主尽快到 https://github.com/apshuang/nonebot-plugin-guess-song 下载资源吧！")
    group_id = str(event.group_id)
    game_name = "chart"
    if check_game_disable(group_id, game_name):
        await matcher.finish(f"本群禁用了{game_alias_map[game_name]}游戏，请联系管理员使用“/开启猜歌 {game_alias_map[game_name]}”来开启游戏吧！")
    await isplayingcheck(group_id, matcher)
    params = args.extract_plain_text().strip().split()
    if len(params) == 0:
        # 没有参数的谱面猜歌
        if len(general_charts_pool) == 0:
            await matcher.finish("当前还没有准备好的谱面噢，请过15秒再尝试一下吧！如果反复出现该问题，请联系bot主扩大preload容量！", reply_message=True)
        (question_clip_path, answer_clip_path) = general_charts_pool.pop(random.randint(0, len(general_charts_pool) - 1))
        await guess_chart_handler(group_id, matcher, question_clip_path, answer_clip_path)
    else:
        gameplay_list[group_id] = {}
        gameplay_list[group_id]["chart"] = {}  # 先占住坑，因为制作视频的时间很长，防止在此期间有其它猜歌请求
        random_music = filter_random(chart_total_list, params, 1)
        if not random_music:
            gameplay_list.pop(group_id)
            await matcher.finish(fault_tips, reply_message=True)
        await matcher.send("使用带参数的谱面猜歌需要等待15秒左右噢！带参数游玩推荐使用“连续谱面猜歌”，等待时间会缩短很多！", reply_message=True)
        random_music = random_music[0]
        
        sub_path_name = f"{str(event.group_id)}_{'_'.join(params)}"
        output_folder = chart_preload_path / sub_path_name
        random_music_id = random_music.id
        music_mp4_file = id_mp4_file_map[random_music_id]
        music_mp3_file = id_mp3_file_map[random_music_id]
        
        # 使用异步线程才能保证其他任务不被影响
        start_time, clip_path = await asyncio.to_thread(random_video_clip, music_mp4_file, CLIP_DURATION, random_music_id, output_folder)
        make_answer_task = asyncio.create_task(make_answer_video(music_mp4_file, music_mp3_file, random_music_id, output_folder, start_time, CLIP_DURATION))
        answer_clip_path = os.path.join(output_folder, f"{random_music_id}_{int(start_time)}_answer_clip.mp4")
        await guess_chart_handler(group_id, matcher, clip_path, answer_clip_path)
        
        # 带参数的谱面猜歌要自己管好自己的文件
        now = datetime.now()
        now_timestamp = int(now.timestamp())
        groupID_folder2delete_timestamp_list.append((group_id, chart_preload_path / sub_path_name, now_timestamp))
        

@continuous_guess_chart.handle()
async def _(event: GroupMessageEvent, matcher: Matcher, args: Message = CommandArg()):
    if len(chart_total_list) == 0:
        await matcher.finish("文件夹没有下载任何谱面视频资源，请让bot主尽快到 https://github.com/apshuang/nonebot-plugin-guess-song 下载资源吧！")
    group_id = str(event.group_id)
    game_name = "chart"
    if check_game_disable(group_id, game_name):
        await matcher.finish(f"本群禁用了{game_alias_map[game_name]}游戏，请联系管理员使用“/开启猜歌 {game_alias_map[game_name]}”来开启游戏吧！")
    await isplayingcheck(group_id, matcher)
    await matcher.send('连续谱面猜曲已开启，发送\"停止\"以结束')
    continuous_stop[group_id] = 1
    charts_pool = None
    params = args.extract_plain_text().strip().split()
    if len(params) == 0:
        # 没有参数的连续谱面猜歌（和普通的区别不大）
        charts_pool = general_charts_pool
    else:
        # 有参数的连续谱面猜歌
        valid_music = filter_random(chart_total_list, params, 10)  # 至少需要有10首歌，不然失去“猜”的价值
        if not valid_music:
            continuous_stop.pop(group_id)
            await matcher.finish(fault_tips)
            
        groupID_params_map[group_id] = params
        sub_path_name = f"{str(event.group_id)}_{'_'.join(params)}"
        param_charts_pool.setdefault(sub_path_name, [])
        charts_pool = param_charts_pool[sub_path_name]
        make_param_chart_task = asyncio.create_task(make_param_chart_video(group_id, params))
        await matcher.send("使用带参数的谱面猜歌，如果猜得太快可能会导致谱面文件来不及制作噢，请稍微耐心等待一下")
    
    while continuous_stop.get(group_id):
        if gameplay_list.get(group_id) is None:
            for i in range(30):
                if len(charts_pool) > 0:
                    break
                await asyncio.sleep(1)
            if len(charts_pool) == 0:
                continuous_stop.pop(group_id)
                groupID_params_map.pop(group_id)
                await matcher.finish("bot主的电脑太慢啦，过了30秒还没有一个谱面制作出来！建议vivo50让我换电脑！", reply_message=True)
            (question_clip_path, answer_clip_path) = charts_pool.pop(random.randint(0, len(charts_pool) - 1))
            await guess_chart_handler(group_id, matcher, question_clip_path, answer_clip_path)
            await asyncio.sleep(1.5)
        try:
            if continuous_stop[group_id] > 3:
                continuous_stop.pop(group_id)
                groupID_params_map.pop(group_id)
                await matcher.finish('没人猜了？ 那我下班了。')
        except Exception as e:
            print(f"continuous guess chart error: {e}")
        await asyncio.sleep(2.5)    
        
    if len(params) != 0:   
        # 带参数的谱面猜歌要自己管好自己的文件
        now = datetime.now()
        now_timestamp = int(now.timestamp())
        groupID_folder2delete_timestamp_list.append((group_id, chart_preload_path / sub_path_name, now_timestamp))
    

async def guess_chart_handler(group_id, matcher: Matcher, question_clip_path, answer_clip_path):
    # 进来之前必须保证question视频已经准备好
    gameplay_list[group_id] = {}
    gameplay_list[group_id]["chart"] = answer_clip_path  # 将answer的路径存下来，方便猜歌以及主动停止时使用
    charts_save_list.append(question_clip_path)  # 存住它，不让这个“单身谱面”被删除，同时也让它不被其它任务当作一个完整谱面
    charts_save_list.append(answer_clip_path)
    
    await matcher.send("这个谱面截取的一个片段如下。请回复“猜歌xxx/开歌xxx”或直接发送别名来猜歌，或回复“不猜了“来停止游戏。", reply_message=True)
    await matcher.send(MessageSegment.video(f"file://{question_clip_path}"))
    
    os.remove(question_clip_path)  # 用完马上删，防止被其它任务拿到
    charts_save_list.remove(question_clip_path)
    
    for _ in range(GUESS_TIME):
        await asyncio.sleep(1)
        if gameplay_list.get(group_id) is None or not gameplay_list[group_id].get("chart") or gameplay_list[group_id].get("chart") != answer_clip_path:
            if continuous_stop.get(group_id):
                continuous_stop[group_id] = 1
            return
        
    random_music_id, start_time = split_id_from_path(question_clip_path)
    is_remaster = False
    if int(random_music_id) > 500000:
        # 是白谱，需要找回原始music对象
        random_music_id = str(int(random_music_id) % 500000)
        is_remaster = True
    random_music = total_list.by_id(random_music_id)
    
    gameplay_list.pop(group_id)  # 需要先pop，不然的话发了答案之后还能猜
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
    if continuous_stop.get(group_id):
        continuous_stop[group_id] += 1


async def make_param_chart_video(group_id, params):
    sub_path_name = f"{str(group_id)}_{'_'.join(params)}"
    
    param_chart_path: Path = chart_preload_path / sub_path_name
    while groupID_params_map.get(group_id) == params:
        while len(param_charts_pool[sub_path_name]) >= PARAM_PRELOAD_CNT:
            if groupID_params_map.get(group_id) != params:
                return
            await asyncio.sleep(5)

        random_music = filter_random(chart_total_list, params, 1)[0]  # 前面已经做过检验，保证过可以
        random_music_id = random_music.id

        music_mp4_file = id_mp4_file_map[random_music_id]
        music_mp3_file = id_mp3_file_map[random_music_id]
        
        # 使用异步线程才能保证其他任务不被影响
        start_time, clip_path = await asyncio.to_thread(random_video_clip, music_mp4_file, CLIP_DURATION, random_music_id, param_chart_path)
        
        make_answer_task = asyncio.create_task(make_answer_video(music_mp4_file, music_mp3_file, random_music_id, param_chart_path, start_time, CLIP_DURATION))
        answer_clip_path = os.path.join(param_chart_path, f"{random_music_id}_{int(start_time)}_answer_clip.mp4")
        param_charts_pool[sub_path_name].append((clip_path, answer_clip_path))
        await asyncio.sleep(20)  # 这个时间建议取make单个视频的时间（15s）再加5s
        
                
async def make_chart_video():
    if len(chart_total_list) == 0:
        # 如果没有配置任何谱面源文件资源，便直接跳出
        return
    await init_chart_pool_by_existing_files(chart_preload_path, general_charts_pool)
    if len(general_charts_pool) < PRELOAD_CNT:
        random_music = random.choice(chart_total_list)
        random_music_id = random_music.id

        music_mp4_file = id_mp4_file_map[random_music_id]
        music_mp3_file = id_mp3_file_map[random_music_id]
        
        # 使用异步线程才能保证其他任务不被影响
        start_time, clip_path = await asyncio.to_thread(random_video_clip, music_mp4_file, CLIP_DURATION, random_music_id, chart_preload_path)
        
        make_answer_task = asyncio.create_task(make_answer_video(music_mp4_file, music_mp3_file, random_music_id, chart_preload_path, start_time, CLIP_DURATION))
        answer_clip_path = await make_answer_task
        
        general_charts_pool.append((clip_path, answer_clip_path))
    

async def init_chart_pool_by_existing_files(root_directory, pool: List, force = False):
    os.makedirs(root_directory, exist_ok=True)
    question_pattern = re.compile(r"(\d+)_([\d\.]+)_clip\.mp4")
    answer_pattern = re.compile(r"(\d+)_([\d\.]+)_answer_clip\.mp4")
    
    files = set(os.listdir(root_directory))
    question_files = {(m.group(1), m.group(2)): os.path.join(root_directory, f) for f in files if (m := question_pattern.match(f))}
    answer_files = {(m.group(1), m.group(2)): os.path.join(root_directory, f) for f in files if (m := answer_pattern.match(f))}
    
    matched_keys = question_files.keys() & answer_files.keys()
    existing_charts = []
    for key in matched_keys:
        if question_files[key] in charts_save_list:
            # 说明这个谱面已经被使用了，即使它暂时还同时有question和answer视频对，我们也不能再重复地使用了
            continue
        existing_charts.append((question_files[key], answer_files[key]))
    
    old_pool = set(pool)
    new_charts = [chart for chart in existing_charts if chart not in old_pool]
    pool.extend(new_charts)
    
    unmatched_files = (set(question_files.values()) | set(answer_files.values())) - set(sum(pool, ()))
    for file in unmatched_files:
        if force or file not in charts_save_list:
            # 只在第一次启动时强制删除单身谱面
            os.remove(file)
            print(f"Deleted: {file}")
        
    # 删掉那些参数谱面猜歌的文件夹
    global groupID_folder2delete_timestamp_list
    todelete_dict = {}
    # 只保留更新的删除请求
    for groupID, path, timestamp in groupID_folder2delete_timestamp_list:
        key = (groupID, path)
        
        if key not in todelete_dict or timestamp > todelete_dict[key][2]:
            todelete_dict[key] = (groupID, path, timestamp)

    groupID_folder2delete_timestamp_list = list(todelete_dict.values())
    for (group_id, folder2delete, timestamp) in groupID_folder2delete_timestamp_list:
        if not os.path.exists(folder2delete):
            groupID_folder2delete_timestamp_list.remove((group_id, folder2delete, timestamp))
        if continuous_stop.get(group_id) is not None or gameplay_list.get(group_id) is not None:
            continue
        now = datetime.now()
        now_timestamp = int(now.timestamp())
        if now_timestamp - timestamp <= TIME_TO_DELETE:
            continue
        shutil.rmtree(folder2delete)
        groupID_folder2delete_timestamp_list.remove((group_id, folder2delete, timestamp))
        
    if force:
        # 在启动的时候，删除一些之前的没用的参数谱面
        valid_folders = set()
        for group_id, params in groupID_params_map.items():
            sub_path_name = f"{group_id}_{'_'.join(params)}"
            valid_folders.add(sub_path_name)
        
        for folder_name in os.listdir(root_directory):
            folder_path = os.path.join(root_directory, folder_name)
            
            if os.path.isdir(folder_path) and folder_name not in valid_folders:
                try:
                    shutil.rmtree(folder_path)
                    print(f"已删除文件夹: {folder_path}")
                except Exception as e:
                    print(f"删除文件夹 {folder_path} 时出错: {e}")
    

@check_chart_file_completeness.handle()
async def check_chart_files(matcher: Matcher):
    mp3_file_lost_list = []
    mp4_file_lost_list = []
    for music in total_list.music_list:
        if music.genre == "\u5bb4\u4f1a\u5834":
            continue
        if not id_mp3_file_map.get(music.id):
            mp3_file_lost_list.append(music.id)
        if not id_mp4_file_map.get(music.id):
            mp4_file_lost_list.append(music.id)
        if len(music.ds) == 5:
            # 检测白谱
            if not id_mp3_file_map.get(str(int(music.id) + 500000)):
                mp3_file_lost_list.append(str(int(music.id) + 500000))
            if not id_mp4_file_map.get(str(int(music.id) + 500000)):
                mp4_file_lost_list.append(str(int(music.id) + 500000))
    if len(mp3_file_lost_list) == 0 and len(mp4_file_lost_list) == 0:
        await matcher.finish("mp3和mp4文件均完整，请放心进行谱面猜歌")
    if len(mp3_file_lost_list) != 0:
        await matcher.send(f"当前一共缺失了{len(mp3_file_lost_list)}首mp3文件，缺失的歌曲id如下{','.join(mp3_file_lost_list)}。其中大于500000的id是白谱资源。")
    if len(mp4_file_lost_list) != 0:
        await matcher.send(f"当前一共缺失了{len(mp4_file_lost_list)}首mp4文件，缺失的歌曲id如下{','.join(mp4_file_lost_list)}。其中大于500000的id是白谱资源。")
        

async def init_chart_guess_info():
    global id_music_map
    for dirpath, dirnames, filenames in os.walk(chart_file_path):
        for file in filenames:
            file_id = os.path.splitext(file)[0]
            if "remaster" in dirpath:
                file_id = str(500000 + int(file_id))
            if file.endswith(".mp3"):
                id_mp3_file_map[file_id] = os.path.join(dirpath, file)
            elif file.endswith(".mp4"):
                id_mp4_file_map[file_id] = os.path.join(dirpath, file)
    common_music_list = list(id_mp3_file_map.keys() & id_mp4_file_map.keys())
    id_to_music = {music.id: music for music in total_list.music_list}
    id_music_map = {id: id_to_music[str(int(id) % 500000)] for id in common_music_list if str(int(id) % 500000) in id_to_music}
    for id, music in id_music_map.items():
        new_music = copy.deepcopy(music)
        if int(id) > 500000:
            # 白谱处理，将白谱的内容（定数、谱面信息等全部顶到紫谱的位置）
            new_music.id = id
            new_music.ds[3] = new_music.ds[4]
            new_music.level[3] = new_music.level[4]
            new_music.cids[3] = new_music.cids[4]
            new_music.charts[3] = new_music.charts[4]
        
        if len(new_music.ds) == 5:
            # 即有白谱的music
            new_music.ds.pop(4)
            new_music.level.pop(4)
            new_music.cids.pop(4)
            new_music.charts.pop(4)
        chart_total_list.append(new_music)
        
    
asyncio.run(init_chart_guess_info())
asyncio.run(init_chart_pool_by_existing_files(chart_preload_path, general_charts_pool, True))
scheduler.add_job(make_chart_video, 'interval', seconds=PRELOAD_CHECK_TIME)
