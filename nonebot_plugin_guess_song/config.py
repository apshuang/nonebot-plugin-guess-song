from pathlib import Path
from pydantic import BaseModel
from textwrap import dedent

from nonebot import get_plugin_config
from nonebot.plugin import require

require("nonebot_plugin_localstore")

import nonebot_plugin_localstore as store


class Config(BaseModel):
    character_filter_japenese: bool = True

game_config = get_plugin_config(Config)

plugin_data_dir: Path = store.get_plugin_data_dir()

guess_static_resources_path: Path = plugin_data_dir / "static"
guess_resources_path: Path = plugin_data_dir / "resources"

music_cover_path: Path = guess_static_resources_path / "mai/cover"
music_info_path: Path = guess_static_resources_path / "music_data.json"
music_alias_path: Path = guess_static_resources_path / "music_alias.json"
font_path: Path = guess_static_resources_path / "SourceHanSansSC-Bold.otf"

user_info_path: Path = guess_resources_path / "user_info.json"  # 基本只用于用户加分
game_data_path: Path = guess_resources_path / "game_data.json"  # 需要记录用户猜对的数量以及每个群猜曲绘的配置数据

game_pic_path: Path = guess_resources_path / "maimai"
music_file_path: Path = guess_resources_path / "music_guo"
chart_file_path: Path = guess_resources_path / "chart_resources"
chart_preload_path: Path = guess_resources_path / "chart_preload"


point_per_credit_dict: dict[str, int] = {
    "listen": 5,
    "open_character": 5,
    "cover": 5,
    "clue": 3,
    "chart": 2
}

levelList: list[str] = ['1', '2', '3', '4', '5', '6', '7', '7+', '8', '8+', '9', '9+', '10', '10+', '11', '11+', '12', '12+', '13', '13+', '14', '14+', '15']
plate_to_version: dict[str, str] = {
    '初': 'maimai',
    '真': 'maimai PLUS',
    '超': 'maimai GreeN',
    '檄': 'maimai GreeN PLUS',
    '橙': 'maimai ORANGE',
    #'暁': 'maimai ORANGE PLUS',
    '晓': 'maimai ORANGE PLUS',
    '桃': 'maimai PiNK',
    #'櫻': 'maimai PiNK PLUS',
    '樱': 'maimai PiNK PLUS',
    '紫': 'maimai MURASAKi',
    #'菫': 'maimai MURASAKi PLUS',
    '堇': 'maimai MURASAKi PLUS',
    '白': 'maimai MiLK',
    '雪': 'MiLK PLUS',
    #'輝': 'maimai FiNALE',
    '辉': 'maimai FiNALE',
    '熊': 'maimai でらっくす',
    #'華': 'maimai でらっくす PLUS',
    '华': 'maimai でらっくす PLUS',
    '爽': 'maimai でらっくす Splash',
    '煌': 'maimai でらっくす Splash PLUS',
    '宙': 'maimai でらっくす UNiVERSE',
    '星': 'maimai でらっくす UNiVERSE PLUS',
    '祭': 'maimai でらっくす FESTiVAL',
    '祝': 'maimai でらっくす FESTiVAL PLUS',
    '双': 'maimai でらっくす BUDDiES'
}

labelmap = {'华': '熊', '華': '熊', '煌': '爽', '星': '宙', '祝': '祭'} #国服特供
category: dict[str, str] = {
    '流行&动漫': 'anime',
    '舞萌': 'maimai',
    'niconico & VOCALOID': 'niconico',
    '东方Project': 'touhou',
    '其他游戏': 'game',
    '音击&中二节奏': 'ongeki',
    'POPSアニメ': 'anime',
    'maimai': 'maimai',
    'niconicoボーカロイド': 'niconico',
    '東方Project': 'touhou',
    'ゲームバラエティ': 'game',
    'オンゲキCHUNITHM': 'ongeki',
    '宴会場': '宴会场'
}

charterlist: dict[str, list[str]] = {
    "0": [
        "-"
    ],
    "1": [
        "譜面-100号",
        "100号",
        "譜面-100号とはっぴー",
        "谱面100号"
    ],
    "2": [
        "ニャイン",
        "二爷",
        "二大爷",
        "二先生"
    ],
    "3": [
        "happy",
        "はっぴー",
        "譜面-100号とはっぴー",
        "はっぴー星人",
        "はぴネコ(はっぴー&ぴちネコ)",
        "緑風 犬三郎",
        "Sukiyaki vs Happy",
        "はっぴー respects for 某S氏",
        "Jack & はっぴー vs からめる & ぐるん",
        "はっぴー & サファ太",
        "舞舞10年ズ（チャンとはっぴー）",
        "哈皮",
        "“H”ack",   #happy + jack
        "“H”ack underground",
        "原田",     #ow谱师 = happy
        "原田ひろゆき"
    ],
    "4": [
        "dp",
        "チャン@DP皆伝",
        "チャン@DP皆伝 vs シチミヘルツ",
        "dp皆传",
        "DP皆传",
        "dq皆传"
    ],
    "5": [
        "jack",
        "Jack",
        "“H”ack",
        "JAQ",
        "7.3Hz＋Jack",
        "チェシャ猫とハートのジャック",
        "“H”ack underground",
        "jacK on Phoenix",
        "Jack & Licorice Gunjyo",
        "Jack & はっぴー vs からめる & ぐるん",
        "jacK on Phoenix & -ZONE- SaFaRi",
        "Jack vs あまくちジンジャー",
        "Garakuta Scramble!"        #gdp + 牛奶 = 小鸟游 + jack
    ],
    "6": [
        "桃子猫",
        "ぴちネコ",
        "SHICHIMI☆CAT",
        "チェシャ猫とハートのジャック",
        "はぴネコ(はっぴー&ぴちネコ)",
        "アマリリスせんせえ with ぴちネコせんせえ",
        "猫",
        "ネコトリサーカス団",
        "ロシアンブラック"  #russianblack = 俄罗斯黑猫 = 桃子猫
    ],
    "7": [
        "maistar",
        "mai-Star",
        "迈斯达"
    ],
    "8": [
        "rion",
        "rioN"
    ],
    "9": [
        "科技厨房",
        "Techno Kitchen"
    ],
    "10": [
        "奉行",
        "すきやき奉行",
        "Sukiyaki vs Happy"
    ],
    "11": [
        "合作",         #不署名多人统一处理
        "合作だよ",
        "maimai TEAM",
        "みんなでマイマイマー",
        "譜面ボーイズからの挑戦状",
        "PANDORA BOXXX",
        "PANDORA PARADOXXX",
        "舞舞10年ズ ～ファイナル～",
        "ゲキ*チュウマイ Fumen Team",
        "maimai Fumen All-Stars",
        "maimai TEAM DX",
        "BEYOND THE MEMORiES",
        "群星"
    ],
    "12": [
        "某S氏",
        "はっぴー respects for 某S氏"
    ],
    "13": [
        "monoclock",
        "ものくろっく",
        "ものくロシェ",
        "一ノ瀬 リズ"   #马甲
    ],
    "14": [
        "柠檬",
        "じゃこレモン",
        "サファ太 vs じゃこレモン",
        "僕の檸檬本当上手"
    ],
    "15": [
        "小鸟游",
        "小鳥遊さん",
        "Phoenix",
        "-ZONE-Phoenix",
        "小鳥遊チミ",
        "小鳥遊さん fused with Phoenix",
        "7.3GHz vs Phoenix",
        "jacK on Phoenix",
        "The ALiEN vs. Phoenix",
        "小鳥遊さん vs 華火職人",
        "red phoenix",
        "小鳥遊さん×アミノハバキリ",
        "Garakuta Scramble!"
    ],
    "16": [
        "moonstrix",
        "Moon Strix"
    ],
    "17": [
        "玉子豆腐"
    ],
    "18": [
        "企鹅",
        "ロシェ@ペンギン",
        "ものくロシェ"
    ],
    "19": [
        "7.3",
        "シチミヘルツ",
        "7.3Hz＋Jack",
        "シチミッピー",
        "Safata.Hz",
        "7.3GHz",
        "七味星人",
        "7.3連発華火",
        "SHICHIMI☆CAT",
        "超七味星人",
        "小鳥遊チミ",
        "Hz-R.Arrow",
        "あまくちヘルツ",
        "Safata.GHz",
        "7.3GHz vs Phoenix",
        "しちみりこりす",
        "7.3GHz -Før The Legends-",
        "チャン@DP皆伝 vs シチミヘルツ"
    ],
    "21": [
        "revo",
        "Revo@LC"
    ],
    "22": [
        "沙发太",
        "サファ太",
        "safaTAmago",
        "Safata.Hz",
        "Safata.GHz",
        "-ZONE- SaFaRi",
        "サファ太 vs -ZONE- SaFaRi",
        "サファ太 vs じゃこレモン",
        "サファ太 vs 翠楼屋",
        "jacK on Phoenix & -ZONE- SaFaRi",
        "DANCE TIME(サファ太)",
        "はっぴー & サファ太",
        "さふぁた",
        "脆脆鲨",       #翠楼屋 + 沙发太
        "ボコ太",
        "鳩サファzhel",
        "Ruby"          #squad谱师 = 沙发太
    ],
    "23": [
        "隅田川星人",
        "七味星人",
        "隅田川華火大会",
        "超七味星人",
        "はっぴー星人",
        "The ALiEN",
        "The ALiEN vs. Phoenix"
    ],
    "24": [
        "华火职人",
        "華火職人",
        "隅田川華火大会",
        "7.3連発華火",
        "“Carpe diem” ＊ HAN∀BI",
        "小鳥遊さん vs 華火職人",
        "大国奏音"
    ],
    "25": [
        "labi",
        "LabiLabi"
    ],
    "26": [
        "如月",
        "如月 ゆかり"
    ],
    "27": [
        "畳返し"
    ],
    "28": [
        "翠楼屋",
        "翡翠マナ",
        "作譜：翠楼屋",
        "KOP3rd with 翡翠マナ",
        "Redarrow VS 翠楼屋",
        "翠楼屋 vs あまくちジンジャー",
        "サファ太 vs 翠楼屋",
        "翡翠マナ -Memoir-",
        "脆脆鲨",
        "Ruby"
    ],
    "29": [
        "鸽子",
        "鳩ホルダー",
        "鳩ホルダー & Luxizhel",
        "鳩サファzhel",
        "鸠",
        "九鸟"
    ],
    "30": [
        "莉莉丝",
        "アマリリス",
        "アマリリスせんせえ",
        "アマリリスせんせえ with ぴちネコせんせえ"
    ],
    "31": [
        "redarrow",
        "Redarrow",
        "Hz-R.Arrow",
        "red phoenix",
        "Redarrow VS 翠楼屋",
        "红箭"
    ],
    "32": [
        "泸溪河",
        "Luxizhel",
        "鳩ホルダー & Luxizhel",
        "桃酥",
        "鳩サファzhel"
    ],
    "33": [
        "amano",
        "アミノハバキリ",
        "小鳥遊さん×アミノハバキリ"
    ],
    "34": [
        "甜口姜",
        "あまくちジンジャー",
        "あまくちヘルツ",
        "翠楼屋 vs あまくちジンジャー",
        "Jack vs あまくちジンジャー"
    ],
    "35": [
        "カマボコ君",
        "ボコ太"
    ],
    "36": [
        "rintarosoma",
        "rintaro soma"
    ],
    "37": [
        "味增",
        "みそかつ侍"
    ],
    "38": [
        "佑"
    ],
    "39": [
        "群青リコリス"
    ],
    "41": [
        "しろいろ"
    ],
    "42": [
        "ミニミライト"
    ],
    "43": [
        "メロンポップ",
        "ずんだポップ"
    ]
}

guess_help_message = dedent('''
            猜歌游戏介绍：
            猜曲绘：根据曲绘猜歌
            听歌猜曲：根据歌曲猜歌
            谱面猜歌：根据谱面猜歌
            线索猜歌：根据歌曲信息猜歌
            开字母：每次可选择揭开一个字母(将歌名中该字母的位置显现出来)，或者选择根据已有信息猜一首歌。从支离破碎的信息中，破解歌曲的名称。
            随机猜歌：从猜曲绘、线索猜歌、听歌猜曲中随机选择一种猜歌方式

            游戏命令（直接输左侧的任一命令）：
            /开字母 /猜曲绘 /线索猜歌 /听歌猜曲 /谱面猜歌 /随机猜歌 - 开始游戏
            /连续猜曲绘 /连续听歌猜曲 /连续线索猜歌 /连续谱面猜歌 /连续随机猜歌 - 开始连续游戏
            开<字母> - 开字母游戏中用于开对应字母
            (猜歌/开歌) <歌名/别名/id> - 猜歌
            不玩了 - 结束本轮游戏
            停止 - 停止连续游戏
            强制停止 - 强制停止所有游戏（在遇到非预期情况时，可以使用该指令强行恢复）
                            
            其他命令：
            /猜歌帮助 - 查看帮助
            /前三 - 查看今日截至当前的答对数量的玩家排名
            /查看谱师 - 查看可用谱师
                            
            管理员命令：
            /猜曲绘配置 <参数> - 配置猜曲绘游戏难度，详细帮助可直接使用此命令查询
            /检查谱面完整性 - 检查谱面猜歌所需的谱面源文件的完整性
            /检查歌曲文件完整性 - 检查听歌猜曲所需的音乐源文件的完整性
            /开启猜歌 <游戏名/all> - 开启某类或全部猜歌游戏
            /关闭猜歌 <游戏名/all> - 关闭某类或全部猜歌游戏
            
            说明：
            一个群内只能同时玩一个游戏。
            玩游戏可获得积分，不同游戏获得的积分不同(谱面猜歌每2首1积分，线索猜歌每3首1积分，其他每5首1积分)。
            
            开始游戏、开始连续游戏的命令都可附加参数，命令后面接若干个参数，每个参数用空格隔开。（可以看最下方的示例参照使用）
            可用参数有：
                版本<版本名> - 可用版本有：初、真、超、檄、橙、晓、桃、樱、紫、堇、白、雪、辉、熊、华、爽、煌、宙、星、祭、祝、双。
                分区<分区名> - 可用分区有：anime、maimai、niconico、touhou、game、ongeki。
                谱师<谱师名> - 可用谱师可用“/查看谱师”命令查询。
                等级<等级> - 只考虑歌曲的紫谱及白谱(如有)。可用等级为1-15。
                定数<定数> - 只考虑歌曲的紫谱及白谱(如有)。可用定数为1.0-15.0。
                新 旧 sd dx - 新为在b35的歌；旧为在b15的歌；sd为标准谱；dx为dx谱。
            同类参数取并集，不同类参数取交集。
            所有参数都可以添加前缀“-”表示排除该条件。
            版本、等级、定数可在自选参数前添加 >= > <= < 中之一表示范围选择。
            附上版本参数的正则表达式：'^(-?)版本([<>]?)(\\=?)(.)$'。
                            
            示例：
            /开字母
            /猜曲绘 定数14.0
            /连续随机猜歌 谱师沙发太 分区maimai -版本<=檄 等级>12+ (指定了谱师和分区，版本不包含初真超檄，等级大于12+)
''')         

superuser_help_message = dedent('''
            猜曲绘配置指令可用参数有：
                cut = [0,1) 控制切片大小的比例，默认为0.5
                gauss = [0,无穷) 控制模糊程度，默认为10
                shuffle = [0,1) 控制打乱方块大小的比例，建议取1/n，默认为0.1
                gray = [0,1] 控制灰度程度，默认为0.8
                transpose = 0 or 1 是否开启旋转及翻转，默认为0
            每次游戏从前三属性中三选一，再分别随机选择是否应用后两个效果。
            因此需确保前三属性不能同时为0。
            ---
            示例：
            /猜曲绘配置 cut=0.5 gray=0.8        
''')