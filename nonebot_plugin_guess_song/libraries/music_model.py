import re
import json 

from ..config import *

def contains_japanese(text):
    # 日文字符的 Unicode 范围包括平假名、片假名、以及部分汉字
    japanese_pattern = re.compile(r'[\u3040-\u30FF\u4E00-\u9FAF]')
    return bool(japanese_pattern.search(text))


class Chart():

    def __init__(self, data: dict):
        note_list = data['notes']
        self.tap = note_list[0]
        self.hold = note_list[1]
        self.slide = note_list[2]
        self.brk = note_list[3]
        if len(note_list) == 5:
            self.touch = note_list[3]
            self.brk = note_list[4]
        else:
            self.touch = 0
        self.charter = data['charter']
        self.note_sum = self.tap + self.slide + self.hold + self.brk + self.touch


class Music():

    diff: list[int] = []
    alias: list[str] = []

    def __init__(self, data: dict):
        # 从字典中获取值并设置类的属性
        self.id: str = data['id']
        self.title: str = data['title']
        self.type: str = data['type']
        self.ds: list[float] = data['ds']
        self.level: list[str] = data['level']
        self.cids: list[int] = data['cids']
        self.charts: list[Chart] = [Chart(chart) for chart in data['charts']]
        self.artist: str = data['basic_info']['artist']
        self.genre: str = data['basic_info']['genre']
        self.bpm: float = data['basic_info']['bpm']
        self.release_date: str = data['basic_info']['release_date']
        self.version: str = data['basic_info']['from']
        self.is_new: bool = data['basic_info']['is_new']

class MusicList():
    music_list: list[Music] = []
    
    def __init__(self, data: list):
        for music_data in data:
            music = Music(music_data)
            self.music_list.append(music)

    def init_alias(self, data: list):
        cache_dict = {}
        for alias_info in data:
            cache_dict[str(alias_info.get("SongID"))] = alias_info.get("Alias")
        for music in self.music_list:
            music.alias = cache_dict.get(music.id, [])
    
    
    def by_id(self, music_id: str) -> Music|None:
        for music in self.music_list:
            if music.id == music_id:
                return music
        return None


def init_music_names():

    global total_list, alias_dict, filter_list

    def load_data(data_path):
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return []

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
    "note": "note音猜歌",
}

game_alias_map_reverse = {
    "开字母" : "open_character",
    "听歌猜曲" : "listen",
    "猜曲绘" : "cover",
    "线索猜歌" : "clue",
    "谱面猜歌" : "chart",
    "随机猜歌" : "random",
    "note音猜歌": "note",
}   

init_music_names()