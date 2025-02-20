import os
import json
from datetime import datetime
from io import BytesIO
import base64
from PIL import Image
from typing import Union, Optional
import random
from PIL import Image, ImageDraw, ImageFont

from .music_model import *
from ..config import *

from nonebot.adapters.onebot.v11 import Message, MessageSegment, Bot
from nonebot.matcher import Matcher


def convert_to_absolute_path(input_path):
    input_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), input_path)
    input_path = os.path.normpath(input_path)
    return input_path


def split_id_from_path(file_path):
    if file_path.find('/') != -1:
        # Linux下通过斜杠/来分割
        file_name = file_path.split('/')[-1]
    elif file_path.find('\\') != -1:
        # Windows下通过反斜杠\来分割
        file_name = file_path.split('\\')[-1]
    music_id = file_name.split('_')[0]
    start_time = file_name.split('_')[1]
    return music_id, start_time


def get_cover_len5_id(mid) -> str:
    '''获取曲绘id'''
    mid = int(mid)
    mid %= 10000
    if mid > 10000 and mid <= 11000:
        mid -= 10000
    if mid > 1000 and mid <= 10000:
        mid += 10000
    return str(mid)


def get_music_file_path(music: Music):
    '''获取音频路径'''
    music_file_name = (int)(music.id)
    music_file_name %= 10000
    music_file_name = str(music_file_name)
    music_file_name += ".mp3"
    music_file = os.path.join(music_file_path, music_file_name)
    return music_file


def song_txt(music: Music, is_remaster: bool = False):
    '''返回歌曲介绍的message'''
    output = (
        f"{music.id}. {music.title}\n"
        f"艺术家：{music.artist}\n"
        f"分类：{music.genre}\n"
        f"版本：{music.version}\n"
        f"{f'紫谱谱师：{music.charts[3].charter}' if not is_remaster else f'白谱谱师：{music.charts[4].charter}'}\n"
        f"BPM：{music.bpm}\n"
        f"定数：{'/'.join(map(str, music.ds))}"
    )
    pic_path = music_cover_path / (get_cover_len5_id(music.id) + ".png")
    print(pic_path)
    return [
        MessageSegment.image(f"file://{pic_path}"), 
        MessageSegment("text", {"text": output})]
    
    
def image_to_base64(img: Image.Image, format='PNG') -> str:
    output_buffer = BytesIO()
    img.save(output_buffer, format)
    byte_data = output_buffer.getvalue()
    base64_str = base64.b64encode(byte_data).decode()
    return 'base64://' + base64_str


def load_data(data_path):
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    
    
def save_game_data(data, data_path):
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
        
def record_game_success(user_id: int, group_id: int, game_type: str):
    '''记录各用户猜对的次数，作为排行榜'''
    gid = str(group_id)
    uid = str(user_id)
    data = load_game_data_json(gid)

    if data[gid]['rank'][game_type].get(uid) is None:
        data[gid]['rank'][game_type][uid] = 0
    data[gid]['rank'][game_type][uid] += 1
    save_game_data(data, game_data_path)
    
    
def get_top_three(group_id: int, game_type: str):
    gid = str(group_id)
    data = load_game_data_json(gid)
    game_data = data[gid]['rank'][game_type]
    sorted_users = sorted(game_data.items(), key=lambda x: x[1], reverse=True)
    return sorted_users[:3]


async def send_forward_message(bot: Bot, target_group_id, sender_id, origin_messages):
    '''将多条信息合并发出'''
    messages = []
    for msg in origin_messages:
        if not msg:
            continue
        messages.append(
            MessageSegment.node_custom(
                user_id=sender_id,
                nickname="猜你字母bot",
                content=Message(msg)
            )
        )
    if len(messages) == 0:
        return
    try:
        # 该方法适用于拉格兰框架
        res_id = await bot.call_api("send_forward_msg", messages=messages)
        await bot.send_group_msg(group_id=target_group_id, message=Message(MessageSegment.forward(res_id)))
    except Exception as e:
        try:
            # 该方法适用于napcat框架
            res_id = await bot.call_api("send_forward_msg", group_id=target_group_id, messages=messages)
        except Exception as e2:
            print(e2)


def load_game_data_json(gid: str):
    data = load_data(game_data_path)
    data.setdefault(gid, {
        "config": {
            "gauss": 10,
            "cut": 0.5,
            "shuffle": 0.1,
            "gray": 0.8,
            "transpose": False
        },
        "rank": {
            "listen": {},
            "open_character": {},
            "cover": {},
            "clue": {},
            "chart": {}
        },
        "game_enable": {
            "listen": True,
            "open_character": True,
            "cover": True,
            "clue": True,
            "chart": True,
            "random": True
        }
    })
    data[gid].setdefault('config', {
            "gauss": 10,
            "cut": 0.5,
            "shuffle": 0.1,
            "gray": 0.8,
            "transpose": False
        })
    data[gid].setdefault('rank', {
            "listen": {},
            "open_character": {},
            "cover": {},
            "clue": {},
            "chart": {}
        })
    data[gid].setdefault('game_enable', {
            "listen": True,
            "open_character": True,
            "cover": True,
            "clue": True,
            "chart": True,
            "random": True
        })
    data[gid]['rank'].setdefault("listen", {})
    data[gid]['rank'].setdefault("open_character", {})
    data[gid]['rank'].setdefault("cover", {})
    data[gid]['rank'].setdefault("clue", {})
    data[gid]['rank'].setdefault("chart", {})
    return data

async def isplayingcheck(gid, matcher: Matcher):
    gid = int(gid)
    if continuous_stop.get(gid) is not None:
        await matcher.finish(f"当前正在运行连续猜歌，可以发送\"停止\"来结束连续猜歌", reply_message=True)
    if gameplay_list.get(gid) is not None:
        now_playing_game = game_alias_map.get(list(gameplay_list.get(gid).keys())[0])
        await matcher.finish(f"当前有一个{now_playing_game}正在运行，可以发送\"不玩了\"来结束游戏并公布答案", reply_message=True)


def filter_random(data: list[Music], args: list[str], cnt: int = 1) -> Union[list[Music], None]:
    filters = {'other': []}
    flip_filters = {'other': []}
    for param in args:
        if not matchparam(param, filters):
            if param[0] != '-' or not matchparam(param[1:], flip_filters):
                return None
    data = list(filter(lambda x: x.genre != '宴会場', data))
    for func in filters['other']:
        data = list(filter(func, data))
    for func in flip_filters['other']:
        data = list(filter(lambda x: not func(x), data))
    filters.pop('other')
    flip_filters.pop('other')
    for funcs in filters.values():
        def total_func(x):
            result = False
            for func in funcs:
                result |= func(x)
            return result
        data = list(filter(total_func, data))
    for funcs in flip_filters.values():
        def total_flip_func(x):
            result = True
            for func in funcs:
                result &= not func(x)
            return result
        data = list(filter(total_flip_func, data))
    try:
        result = random.sample(data, cnt)
    except ValueError:
        return None
    return result

fault_tips = f'参数错误，可能是满足条件的歌曲数不足或格式错误，可用“/猜歌帮助”命令获取帮助哦！'

def matchparam(param: str, filters: dict) -> bool:
    try:
        if _ := b50listb.get(param):      #过滤参数
            filters['other'].append(_)

        elif _ := re.match(r'^版本([<>]?)(\=?)(.)$', param):
            if (ver := _.group(3)) not in plate_to_version:
                return False
            filters.setdefault('ver', [])
            ver = plate_to_version[labelmap.get(ver) or ver]
            if sign := _.group(1):
                if _.group(2):
                    filter_func = lambda x: ver_filter(x, ver)
                    filters['ver'].append(filter_func)
                for i, _ver in enumerate(verlist := list(plate_to_version.values())):
                    if (sign == '>' and i > verlist.index(ver)) or (sign == '<' and i < verlist.index(ver)):
                        filter_func = lambda x, __ver=_ver: ver_filter(x, __ver)
                        filters['ver'].append(filter_func)
            else:
                filter_func = lambda x: ver_filter(x, ver)
                filters['ver'].append(filter_func)

        elif param[:2] == '分区':
            label = param[2:]
            if label not in category.values():
                return False
            filter_func = lambda x: cat_filter(x, label)
            filters.setdefault('category', [])
            filters['category'].append(filter_func)

        elif param[:2] == '谱师':
            name = param[2:]
            if not (musicdata := find_charter(name)):
                return False
            filter_func = lambda x: charter_filter(x, musicdata)
            filters.setdefault('charter', [])
            filters['charter'].append(filter_func)

        elif _ := re.match(r'^等级([<>]?)(\=?)(.+)$', param):
            if (level := _.group(3)) not in levelList:
                return False
            filters.setdefault('level', [])
            if sign := _.group(1):
                if _.group(2):
                    filter_func = lambda x: level_filter(x, level)
                    filters['level'].append(filter_func)
                for i, _level in enumerate(levelList):
                    if (sign == '>' and i > levelList.index(level)) or (sign == '<' and i < levelList.index(level)):
                        filter_func = lambda x, lv=_level: level_filter(x, lv)
                        filters['level'].append(filter_func)
            else:
                filter_func = lambda x: level_filter(x, level)
                filters['level'].append(filter_func)

        elif _ := re.match(r'^定数([<>]?)(\=?)(\d+\.\d)$', param):
            if not (1.0 <= (ds := float( _.group(3))) <= 15.0):
                return False
            filters.setdefault('ds', [])
            if sign := _.group(1):
                if _.group(2):
                    filter_func = lambda x: ds_filter(x, ds)
                    filters['ds'].append(filter_func)
                for i in range(10, 151):
                    _ds = i / 10
                    if (sign == '>' and _ds > ds) or (sign == '<' and _ds < ds):
                        filter_func = lambda x, __ds=_ds: ds_filter(x, __ds)
                        filters['ds'].append(filter_func)
            else:
                filter_func = lambda x: ds_filter(x, ds)
                filters['ds'].append(filter_func)

        else:
            return False
    except Exception as e:
        print(e)
        return False
    return True


def ver_filter(music: Music, ver: str) -> bool:
    return music.version == ver

def cat_filter(music: Music, cat: str) -> bool:
    genre = music.genre
    if category.get(genre):
        genre = category[genre]
    return genre == cat

def charter_filter(music: Music, musiclist: list) -> bool:
    return music.id in musiclist


def is_new(music: Music) -> bool:
    return music.is_new

def is_old(music: Music) -> bool:
    return not music.is_new

def is_sd(music: Music) -> bool:
    return music.type == 'SD'

def is_dx(music: Music) -> bool:
    return music.type == 'DX'

def level_filter(music: Music, level: str) -> bool:
    return level in music.level[3:] #只考虑紫白谱

def ds_filter(music: Music, ds: float) -> bool:
    return ds in music.ds[3:]   #只考虑紫白谱

b50listb = {
    '新': is_new,
    '旧': is_old,
    'sd': is_sd,
    'dx': is_dx
}

def find_charter(name: str):
    all_music = list(filter(lambda x: x.genre != '宴会場', total_list.music_list))
    white_music = list(filter(lambda x: len(x.charts) == 5, all_music))
    music_data = []
    for namelist in charterlist.values():
        if name in namelist:
            for alias in namelist:
                music_data.extend(list(filter(lambda x: x.charts[3].charter == alias, all_music)))
                music_data.extend(list(filter(lambda x: x.charts[4].charter == alias, white_music)))
    if not len(music_data):
        music_data.extend(list(filter(lambda x: name.lower() in x.charts[3].charter.lower(), all_music)))
        music_data.extend(list(filter(lambda x: name.lower() in x.charts[4].charter.lower(), white_music)))
    return [music.id for music in music_data]

def text_to_image(text: str) -> Image.Image:
    font = ImageFont.truetype(str(game_config.guess_static_resources_path / "SourceHanSansSC-Bold.otf"), 24)
    padding = 10
    margin = 4
    lines = text.strip().split('\n')
    max_width = 0
    b = 0
    for line in lines:
        l, t, r, b = font.getbbox(line)
        max_width = max(max_width, r)
    wa = max_width + padding * 2
    ha = b * len(lines) + margin * (len(lines) - 1) + padding * 2
    im = Image.new('RGB', (wa, ha), color=(255, 255, 255))
    draw = ImageDraw.Draw(im)
    for index, line in enumerate(lines):
        draw.text((padding, padding + index * (margin + b)), line, font=font, fill=(0, 0, 0))
    return im

def to_bytes_io(text: str) -> BytesIO:
    bio = BytesIO()
    text_to_image(text).save(bio, format='PNG')
    bio.seek(0)
    return bio


global_game_data = load_data(game_data_path)

def check_game_disable(gid, game_name):
    global_game_data = load_game_data_json(gid) # 包含一个初始化
    enable_sign = global_game_data[gid]["game_enable"][game_name]
    return not enable_sign