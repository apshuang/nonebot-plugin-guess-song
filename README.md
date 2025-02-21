<div align="center">
  <a href="https://v2.nonebot.dev/store"><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/nbp_logo.png" width="180" height="180" alt="NoneBotPluginLogo"></a>
  <br>
  <p><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/NoneBotPlugin.svg" width="240" alt="NoneBotPluginText"></p>
</div>

<div align="center">

# nonebot-plugin-guess-song

_✨ NoneBot 音游猜歌游戏插件 ✨_


<a href="./LICENSE">
    <img src="https://img.shields.io/github/license/apshuang/nonebot-plugin-guess-song.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-guess-song">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-guess-song.svg" alt="pypi">
</a>
<img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="python">

</div>


## 📖 介绍

一个音游猜歌插件（主要为舞萌DX maimaiDX提供资源），有开字母、猜曲绘、听歌猜曲、谱面猜歌、线索猜歌等游戏

## 💿 安装

<details open>
<summary>使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot-plugin-guess-song

</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details>
<summary>pip</summary>

    pip install nonebot-plugin-guess-song
</details>
<details>
<summary>pdm</summary>

    pdm add nonebot-plugin-guess-song
</details>
<details>
<summary>poetry</summary>

    poetry add nonebot-plugin-guess-song
</details>
<details>
<summary>conda</summary>

    conda install nonebot-plugin-guess-song
</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

    plugins = ["nonebot_plugin_guess_song"]

</details>

## ⚙️ 配置

⚠️⚠️⚠️请务必注意，若需要使用听歌猜曲以及谱面猜歌，必须先下载并配置ffmpeg⚠️⚠️⚠️

⚠️⚠️⚠️若需要使用谱面猜歌，请安装moviepy==1.0.3（最新版本无法使用）⚠️⚠️⚠️

在 nonebot2 项目的`.env`文件中添加下表中的必填配置

| 配置项 | 必填 | 默认值 | 说明 |
|:-----:|:----:|:----:|:----:|
| character_filter_japenese | 否 | True | 指示开字母游戏中，是否需要过滤掉含有日文字符的歌曲 |


### 资源需求
本插件需要一些资源（歌曲信息等）才能够正常使用，以下是说明及下载方法、配置教程。

💡**资源需求说明**：
- 最低配置（所有游戏都需要）：music_data.json、music_alias.json（在后文的static压缩包中）
- 开字母：无需添加其它资源（可以按需添加[“这么难他都会”](https://github.com/apshuang/nonebot-plugin-guess-song/blob/master/so_hard.jpg)的图片资源到/resources/maimai/so_hard.jpg）
- 猜曲绘：需要添加mai/cover（也在后文的static压缩包中）
- 线索猜歌：需要添加mai/cover（如果添加了音乐资源，还会增加歌曲长度作为线索）
- 听歌猜曲：需要添加music_guo——在动态资源路径/resources下，建立music_guo文件夹，将听歌猜曲文件放入内；
- 谱面猜歌：需要添加chart_resources——在动态资源路径/resources下，建立chart_resources文件夹，将谱面猜歌资源文件放入内（保持每个版本一个文件夹）。


🟩**static文件**：[GitHub Releases下载](https://github.com/apshuang/nonebot-plugin-guess-song/releases/tag/Static-resources)、[百度云盘](https://pan.baidu.com/s/1K5d7MqcNh83gh9yerfgGPg?pwd=fiwp)

内部包括music_data.json、music_alias.json文件，以及mai/cover，是歌曲的信息与别名，以及歌曲的曲绘。
推荐联合使用[其它maimai插件](https://github.com/Yuri-YuzuChaN/nonebot-plugin-maimaidx)来动态更新歌曲信息与别名信息。


🟩**动态资源文件**（针对听歌猜曲和谱面猜歌，可**按需下载**）：
- 听歌猜曲文件（共6.55GB，已切分为五个压缩包，可部分下载）：[GitHub Releases下载](https://github.com/apshuang/nonebot-plugin-guess-song/releases/tag/guess_listen-resources)、[百度云盘](https://pan.baidu.com/s/1vVC8p7HDWfczMswOLmE8Og?pwd=gqu3)
- 谱面猜歌文件（共22.37GB，已划分为按版本聚类，可下载部分版本使用）：[GitHub Releases下载](https://github.com/apshuang/nonebot-plugin-guess-song/releases/tag/guess_chart-resources)、[百度云盘](https://pan.baidu.com/s/1kIMeYv46djxJe_p8DMTtfA?pwd=e6sf)

在动态资源路径/resources下，建立music_guo文件夹，将听歌猜曲文件放入内；建立chart_resources文件夹，将谱面猜歌资源文件放入内（保持每个版本一个文件夹）。
⚠️可以不下载动态资源， 也可以只下载部分动态资源（部分歌曲或部分版本），插件也能正常运行，只不过曲库会略微少一些。⚠️

### 资源目录配置教程
<details>
  <summary>点击展开查看项目目录</summary>

  ```plaintext
  CainithmBot/
  ├── static/
  │   ├── mai/
  │   │   └── cover/
  │   ├── music_data.json  # 歌曲信息
  │   ├── music_alias.json  # 歌曲别名信息
  │   └── SourceHanSansSC-Bold.otf  # 发送猜歌帮助所需字体
  ├── resources/
  │   ├── music_guo/  # 国服歌曲音乐文件
  │   │   ├── 8.mp3
  │   │   └── ...
  │   ├── chart_resources/  # 谱面猜歌资源文件
  │   │   ├── 01. maimai/  # 内部需按版本分开各个文件夹
  │   │   │   ├── mp3/
  │   │   │   └── mp4/
  │   │   ├── 02. maimai PLUS/
  │   │   │   ├── mp3/
  │   │   │   └── mp4/
  │   │   └── ...
  │   │   ├── remaster/
  │   │   │   ├── mp3/
  │   │   │   └── mp4/
  └── ...

  ```
</details>


根据上面的项目目录，我们可以看到，在某个存放资源的根目录（假设这个根目录为`E:/Bot/CainithmBot`）下面，有一个static文件夹和一个resources文件夹，只需要按照上面的指示，将对应的资源放到对应文件夹目录下即可。
同时，本插件使用了nonebot-plugin-localstore插件进行资源管理，所以，比较建议您为本插件单独设置一个资源根目录（因为资源较多），我们继续假设这个资源根目录为`E:/Bot/CainithmBot`，那么您需要在`.env`配置文件中添加以下配置：
```dotenv
LOCALSTORE_PLUGIN_DATA_DIR='
{
  "nonebot_plugin_guess_song": "E:/Bot/CainithmBot"
}   
'
```
如果您希望直接使用一个全局的资源根目录，则直接通过`nb localstore`，查看全局的Data Dir，并将static和resources文件夹置于这个Data Dir下，就可以使用了！


## 🎉 使用
### 指令表
详细指令表及其高级用法（比如过滤某个版本、某些等级的歌曲）也可以通过“/猜歌帮助”来查看
| 指令 | 权限 | 需要@ | 范围 | 说明 |
|:-----:|:----:|:----:|:----:|:----:|
| /开字母 | 群员 | 否 | 群聊 | 开始开字母游戏 |
| /(连续)听歌猜曲 | 群员 | 否 | 群聊 | 开始(连续)听歌猜曲游戏 |
| /(连续)谱面猜歌 | 群员 | 否 | 群聊 | 开始(连续)谱面猜歌游戏 |
| /(连续)猜曲绘 | 群员 | 否 | 群聊 | 开始(连续)猜曲绘游戏 |
| /(连续)线索猜歌 | 群员 | 否 | 群聊 | 开始(连续)线索猜歌游戏 |
| 猜歌 xxx | 群员 | 否 | 群聊 | 根据已知信息猜测歌曲 |
| 不玩了 | 群员 | 否 | 群聊 | 揭晓当前猜歌的答案 |
| 停止 | 群员 | 否 | 群聊 | 停止连续猜歌 |
| /开启/关闭猜歌 xxx | 管理员/主人 | 否 | 群聊 | 开启或禁用某类或全部猜歌游戏 |
| /猜曲绘配置 xxx | 管理员/主人 | 否 | 群聊 | 进行猜曲绘配置（高斯模糊程度、打乱程度、裁切程度等） |
| /检查歌曲文件完整性 | 主人 | 否 | 群聊 | 检查听歌猜曲的音乐资源 |
| /检查谱面完整性 | 主人 | 否 | 群聊 | 检查谱面猜歌的文件资源 |


## 📝 项目特点

- ✅ 游戏新颖、有趣，更贴合游戏的核心要素（谱面与音乐）
- ✅ 资源配置要求较低，可按需部分下载
- ✅ 性能较高，使用preload技术加快谱面加载速度
- ✅ 框架通用，可扩展性强
- ✅ 使用简单、可使用别名猜歌，用户猜歌方便
- ✅ 贡献了谱面猜歌数据集，可以用于制作猜歌视频


### 效果图
![开字母效果图](./docs/open_character_screenshot.png)
![猜曲绘效果图](./docs/guess_cover_screenshot.png)
![谱面猜歌效果图](./docs/guess_chart_screenshot.png)


## 🙏 鸣谢

- [maimai插件](https://github.com/Yuri-YuzuChaN/nonebot-plugin-maimaidx) - maimai插件、static资源下载
- [MajdataEdit](https://github.com/LingFeng-bbben/MajdataEdit) - maimai谱面编辑器
- [MajdataEdit_BatchOutput_Tool](https://github.com/apshuang/MajdataEdit_BatchOutput_Tool) - 用于批量导出maimai谱面视频资源
- [NoneBot2](https://github.com/nonebot/nonebot2) - 跨平台 Python 异步机器人框架


## 📞 联系

| 猜你字母Bot游戏群（欢迎加群游玩）  | QQ群：925120177 |
| ---------------- | ---------------- |

发现任何问题或有任何建议，欢迎发Issue，也可以加群联系开发团队，感谢！