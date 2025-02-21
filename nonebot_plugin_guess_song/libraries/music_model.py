import re
import json 
import asyncio
from typing import Dict, List, Optional

from ..config import *

from nonebot import get_plugin_config


config = get_plugin_config(Config)


def contains_japanese(text):
    # 日文字符的 Unicode 范围包括平假名、片假名、以及部分汉字
    japanese_pattern = re.compile(r'[\u3040-\u30FF\u4E00-\u9FAF]')
    return bool(japanese_pattern.search(text))


class Chart():
    tap: Optional[int] = None
    slide: Optional[int] = None
    hold: Optional[int] = None
    brk: Optional[int] = None
    touch: Optional[int] = None
    charter: Optional[str] = None
    note_sum: Optional[int] = None

    def __init__(self, data: Dict):
        note_list = data.get('notes')
        self.tap = note_list[0]
        self.slide = note_list[1]
        self.hold = note_list[2]
        self.brk = note_list[3]
        if len(note_list) == 5:
            self.touch = note_list[3]
            self.brk = note_list[4]
        else:
            self.touch = 0
        self.charter = data.get('charter')
        self.note_sum = self.tap + self.slide + self.hold + self.brk + self.touch


class Music():
    id: Optional[str] = None
    title: Optional[str] = None
    type: Optional[str] = None
    ds: Optional[List[float]] = None
    level: Optional[List[str]] = None
    cids: Optional[List[int]] = None
    charts: Optional[List[Chart]] = None
    artist: Optional[str] = None
    genre: Optional[str] = None
    bpm: Optional[float] = None
    release_date: Optional[str] = None
    version: Optional[str] = None
    is_new: Optional[bool] = None

    diff: List[int] = []
    alias: List[str] = []

    def __init__(self, data: Dict):
        # 从字典中获取值并设置类的属性
        self.id: Optional[str] = data.get('id')
        self.title: Optional[str] = data.get('title')
        self.type: Optional[str] = data.get('type')
        self.ds: Optional[List[float]] = data.get('ds')
        self.level: Optional[List[str]] = data.get('level')
        self.cids: Optional[List[int]] = data.get('cids')
        self.charts: Optional[List[Chart]] = [Chart(chart) for chart in data.get('charts')]
        self.artist: Optional[str] = data.get('basic_info').get('artist')
        self.genre: Optional[str] = data.get('basic_info').get('genre')
        self.bpm: Optional[float] = data.get('basic_info').get('bpm')
        self.release_date: Optional[str] = data.get('basic_info').get('release_date')
        self.version: Optional[str] = data.get('basic_info').get('from')
        self.is_new: Optional[bool] = data.get('basic_info').get('is_new')

class MusicList():
    music_list: Optional[List[Music]] = []
    
    def __init__(self, data: List):
        for music_data in data:
            music = Music(music_data)
            self.music_list.append(music)

    def init_alias(self, data: Dict):
        cache_dict = {}
        for alias_info in data:
            cache_dict[str(alias_info.get("SongID"))] = alias_info.get("Alias")
        for music in self.music_list:
            if cache_dict.get(music.id):
                music.alias = cache_dict.get(music.id)
            else:
                music.alias = []
    
    
    def by_id(self, music_id: str) -> Optional[Music]:
        for music in self.music_list:
            if music.id == music_id:
                return music
        return None


async def main():

    global total_list, alias_dict, filter_list

    def load_data(data_path):
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    music_data = load_data(music_info_path)
    total_list = MusicList(music_data)
    
    alias_data = load_data(music_alias_path)
    total_list.init_alias(alias_data)

    alias_dict = {}
    for i in range(len(total_list.music_list)):
        
        # 将歌曲的id也加入别名
        id = total_list.music_list[i].id
        if alias_dict.get(id) is None:
            alias_dict[id] = [i]
        else:
            alias_dict[id].append(i)
            
        title = total_list.music_list[i].title
        
        # 将歌曲的原名也加入别名（统一转为小写）
        title_lower = title.lower()
        if alias_dict.get(title_lower) is None:
            alias_dict[title_lower] = [i]
        else:
            alias_dict[title_lower].append(i)

        for alias in total_list.music_list[i].alias:
            # 将别名库中的别名载入到内存字典中（统一转为小写）
            alias_lower = alias.lower()
            if alias_dict.get(alias_lower) is None:
                alias_dict[alias_lower] = [i]
            else:
                alias_dict[alias_lower].append(i)
    
    # 对别名字典进行去重
    for key, value_list in alias_dict.items():
        alias_dict[key] = list(set(value_list))
    
    # 选出没有日文字的歌曲，作为开字母的曲库（因为如果曲名有日文字很难开出来）
    filter_list = []
    for music in total_list.music_list:
        if (not game_config.character_filter_japenese) or (not contains_japanese(music.title)):
            # 如果不过滤那就都可以加，如果要过滤，那就不含有日文才能加
            filter_list.append(music)
    
gameplay_list = {}
continuous_stop = {}
game_alias_map = {
    "open_character" : "开字母",
    "listen" : "听歌猜曲",
    "cover" : "猜曲绘",
    "clue" : "线索猜歌",
    "chart" : "谱面猜歌",
    "random" : "随机猜歌",
}

game_alias_map_reverse = {
    "开字母" : "open_character",
    "听歌猜曲" : "listen",
    "猜曲绘" : "cover",
    "线索猜歌" : "clue",
    "谱面猜歌" : "chart",
    "随机猜歌" : "random",
}

asyncio.run(main())
    