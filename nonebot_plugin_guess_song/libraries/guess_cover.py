import random
import asyncio
from typing import Tuple
from PIL import Image, ImageFilter, ImageEnhance

from .utils import *
from .music_model import gameplay_list, alias_dict, total_list, game_alias_map, continuous_stop

from nonebot import on_fullmatch, on_command
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import GroupMessageEvent, GROUP_ADMIN, GROUP_OWNER
from nonebot.permission import SUPERUSER
from nonebot.params import CommandArg


guess_cover_config_dict = {}

continuous_guess_cover = on_command('连续猜曲绘')
guess_cover = on_command('猜曲绘')
guess_cover_config = on_command('猜曲绘配置', permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER)


def apply_gray(im: Image.Image, gray) -> Image.Image:
    gray_im = im.convert('L')
    enhancer = ImageEnhance.Brightness(gray_im)
    semi_gray = enhancer.enhance(0.5)
    result = Image.blend(im.convert('RGBA'), semi_gray.convert('RGBA'), alpha=gray)
    return result

def apply_gauss(im: Image.Image, gauss) -> Image.Image:
    return im.filter(ImageFilter.GaussianBlur(radius = gauss))

def apply_cut(im: Image.Image, cut) -> Image.Image:
    w, h = im.size
    w2, h2 = int(w*cut), int(h*cut)
    l, u = random.randrange(0, int(w-w2)), random.randrange(0, int(h-h2))
    return im.crop((l, u, l + w2, u + h2))

def apply_transpose(im: Image.Image) -> Image.Image:
    angle = random.randint(0, 3) * 90
    im = im.rotate(angle)
    flip = random.randint(0, 2)
    if flip == 1:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    elif flip == 2:
        im = im.transpose(Image.FLIP_TOP_BOTTOM)
    return im

def apply_shuffle(im: Image.Image, shuffle) -> Image.Image:
    """拆分成方块随机排列"""
    w, h = im.size
    block_size = int(w * shuffle)
    blocks = []
    for i in range(0, w, block_size):
        for j in range(0, h, block_size):
            block = im.crop((i, j, i + block_size, j + block_size))
            blocks.append(block)
    random.shuffle(blocks)
    shuffled = Image.new("RGB", im.size)
    idx = 0
    for i in range(0, w, block_size):
        for j in range(0, h, block_size):
            shuffled.paste(blocks[idx], (i, j))
            idx += 1
    return shuffled


vital_apply = {
    'gauss': '模糊',
    'cut': '裁切',
    'shuffle': '打乱',
}


async def pic(path: str, gid: str) -> Tuple[Image.Image, str]:
    im = Image.open(path)
    data = load_game_data_json(gid)
    args = data[gid]['config']
    sample_pool = [name for name,value in args.items() if name in vital_apply.keys() and value != 0]
    pattern = random.sample(sample_pool, 1)
    if pattern[0] == 'gauss':
        im = apply_gauss(im, args['gauss'])
    elif pattern[0] == 'cut':
        im = apply_cut(im, args['cut'])
    elif pattern[0] == 'shuffle':
        im = apply_shuffle(im, args['shuffle'])

    if args['gray'] and random.randint(0,1):
        im = apply_gray(im, float(args['gray']))
    if args['transpose'] and random.randint(0,1):
        im = apply_transpose(im)
    return im, vital_apply[pattern[0]]


def cover_rank_message(group_id):
    top_guess_cover = get_top_three(group_id, "cover")
    if top_guess_cover:
        msg = "今天的前三名猜曲绘王：\n"
        for rank, (user_id, count) in enumerate(top_guess_cover, 1):
            msg += f"{rank}. {MessageSegment.at(user_id)} 猜对了{count}首歌！\n"
        msg += "蓝的盆。。。"
        return msg


async def cover_open_song_handler(matcher, song_name, group_id, user_id, ignore_tag):
    pic_info = gameplay_list.get(group_id).get("cover")

    music_candidates = alias_dict.get(song_name)
    if music_candidates is None:
        if ignore_tag:
            return
        await matcher.finish("没有找到这样的乐曲。请输入正确的名称或别名", reply_message=True)
    
    if len(music_candidates) < 20:
        for music_index in music_candidates:
            music = total_list.music_list[music_index]
            if pic_info.title == music.title:
                gameplay_list.pop(group_id)
                record_game_success(user_id=user_id, group_id=group_id, game_type="cover")
                answer = MessageSegment.text(f'猜对啦！答案是:\n')+song_txt(pic_info)
                await matcher.finish(answer, reply_message=True)
    if not ignore_tag:        
        await matcher.finish("你猜的答案不对噢，再仔细看一下吧！", reply_message=True)
        

@continuous_guess_cover.handle()
async def continuous_guess_cover_handler(event: GroupMessageEvent, matcher: Matcher, args: Message = CommandArg()):
    if len(total_list.music_list) == 0:
        await matcher.finish("本插件还没有配置好static资源噢，请让bot主尽快到 https://github.com/apshuang/nonebot-plugin-guess-song 下载资源吧！")
    gid = str(event.group_id)
    game_name = "cover"
    if check_game_disable(gid, game_name):
        await matcher.finish(f"本群禁用了{game_alias_map[game_name]}游戏，请联系管理员使用“/开启猜歌 {game_alias_map[game_name]}”来开启游戏吧！")
    params = args.extract_plain_text().strip().split()
    await isplayingcheck(gid, matcher)
    if not filter_random(total_list.music_list, params, 1):
        await matcher.finish(fault_tips, reply_message=True)
    await matcher.send('连续猜曲绘已开启，发送\"停止\"以结束')
    continuous_stop[gid] = 1
    while continuous_stop.get(gid):
        if gameplay_list.get(gid) is None:
            await guess_cover_handler(gid, matcher, params)
        if continuous_stop[gid] > 3:
            continuous_stop.pop(gid)
            await matcher.finish('没人猜了？ 那我下班了。')
        await asyncio.sleep(1)


@guess_cover.handle()
async def _(event: GroupMessageEvent, matcher: Matcher, args: Message = CommandArg()):
    if len(total_list.music_list) == 0:
        await matcher.finish("本插件还没有配置好static资源噢，请让bot主尽快到 https://github.com/apshuang/nonebot-plugin-guess-song 下载资源吧！")
    gid = str(event.group_id)
    game_name = "cover"
    if check_game_disable(gid, game_name):
        await matcher.finish(f"本群禁用了{game_alias_map[game_name]}游戏，请联系管理员使用“/开启猜歌 {game_alias_map[game_name]}”来开启游戏吧！")
    params = args.extract_plain_text().strip().split()
    await isplayingcheck(gid, matcher)
    await guess_cover_handler(gid, matcher, params)

async def guess_cover_handler(gid, matcher: Matcher, args):
    if _ := filter_random(total_list.music_list, args, 1):
        random_music = _[0]
    else:
        await matcher.finish(fault_tips, reply_message=True)
    pic_path = music_cover_path / (get_cover_len5_id(random_music.id) + ".png")
    draw, pictype = await pic(pic_path, str(gid))
    gameplay_list[gid] = {}
    gameplay_list[gid]["cover"] = random_music
    await matcher.send(
        MessageSegment.text(f'以下{pictype}图片是哪首歌的曲绘：\n') +
        MessageSegment.image(image_to_base64(draw)) +
        MessageSegment.text('请在30s内输入答案'),
        reply_message=True
    )
    for _ in range(30):
        await asyncio.sleep(1)
        if gameplay_list.get(gid) is None or not gameplay_list[gid].get("cover") or gameplay_list[gid].get("cover") != random_music:
            if continuous_stop.get(gid):
                continuous_stop[gid] = 1
            return
    gameplay_list.pop(gid)
    answer = MessageSegment.text(f'答案是:\n') + song_txt(random_music)
    await matcher.send(answer)
    if continuous_stop.get(gid):
        continuous_stop[gid] += 1


@guess_cover_config.handle()
async def guess_cover_config_handler(event: GroupMessageEvent, matcher: Matcher, arg: Message = CommandArg()):
    gid = str(event.group_id)
    mes = arg.extract_plain_text().split()
    if len(mes) == 0:
        await matcher.finish(MessageSegment.image(to_bytes_io(superuser_help_message)), reply_message=True)
    data = load_game_data_json(gid)
    config = data[gid]['config']
    try:
        for update in mes:
            name, value = update.split('=')
            if name == 'cut':
                value = float(value)
                if value < 0 or value >= 1:
                    raise ValueError
            elif name == 'gauss':
                value = int(value)
                if value < 0:
                    raise ValueError
            elif name == 'gray':
                value = float(value)
                if value < 0 or value > 1:
                    raise ValueError
            elif name == 'transpose':
                value = bool(int(value))
            elif name == 'shuffle':
                value = float(value)
                if value < 0 or value >= 1:
                    raise ValueError
            else:
                raise ValueError
            config[name] = value
    except ValueError:
        await matcher.finish('参数错误' + MessageSegment.image(to_bytes_io(superuser_help_message)), reply_message=True)
    if config['cut'] == 0 and config['gauss'] == 0 and config['shuffle'] == 0:
        config['cut'] = 1
    save_game_data(data, game_data_path)
    await matcher.finish(f'更新配置完成：\n{config}')