import json
import websockets
from config import ClientConfig as Config
from util.client_cosmic import Cosmic, console
from util.client_check_websocket import check_websocket
from util.client_hot_sub import hot_sub
from util.client_rename_audio import rename_audio
from util.client_strip_punc import strip_punc
from util.client_write_md import write_md
from util.client_type_result import type_result
if not Cosmic.transcribe_subtitles:
    from util.client_translate_online import translate_online
    from util.client_translate_offline import translate_offline
import warnings
warnings.filterwarnings ('ignore')

async def recv_result():
    if not await check_websocket():
        return
    console.print('[green]连接成功\n')
    try:
        while True:
            # 接收消息
            message = await Cosmic.websocket.recv()
            message = json.loads(message)
            text = message['text']
            delay = message['time_complete'] - message['time_submit']

            # 如果非最终结果，继续等待
            if not message['is_final']:
                continue

            # 消除末尾标点
            text = strip_punc(text)

            # 热词替换
            text = hot_sub(text)

            # 离线翻译
            offline_translate_done = False
            if Cosmic.offline_translate_needed and not Cosmic.transcribe_subtitles:
                offline_translated_text = await translate_offline(text)
                offline_translate_done = True
                Cosmic.offline_translate_needed = False

            # 在线翻译
            online_translate_done = False
            if Cosmic.online_translate_needed and not Cosmic.transcribe_subtitles:
                online_translated_text = translate_online(text)
                online_translate_done = True
                Cosmic.online_translate_needed = False

            if Config.save_audio:
                # 重命名录音文件
                file_audio = rename_audio(message['task_id'], text, message['time_start'])
                # 记录写入 md 文件
                write_md(text, message['time_start'], file_audio)

            # 控制台输出
            console.print(f'    转录时延：{delay:.2f}s')
            console.print(f'    识别结果：[green]{text}')
            if offline_translate_done:
                console.print(f'    离线翻译结果：[green]{offline_translated_text}')
            if online_translate_done:
                online_translated_text_gbk = online_translated_text.encode('gbk', errors='replace').decode('gbk', errors='replace')
                console.print(f'    在线翻译结果：[green]{online_translated_text_gbk}')
            console.line()

            # 打字
            if offline_translate_done:
                await type_result(offline_translated_text)
                offline_translate_done = False
            elif online_translate_done:
                await type_result(online_translated_text)
                online_translate_done = False
            else:
                await type_result(text)


    except websockets.ConnectionClosedError:
        console.print('[red]连接断开\n')
    except websockets.ConnectionClosedOK:
        console.print('[red]连接断开\n')
    except Exception as e:
        print(e)
    finally:
        return

if __name__ == '__main__':
    None