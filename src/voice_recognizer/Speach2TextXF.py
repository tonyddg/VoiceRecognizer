# -*- coding: utf-8 -*-
import base64
import hashlib
import hmac
import json
import os
import time
from typing import Union
from pathlib import Path
import requests
from dataclasses import dataclass, field
import dotenv

from voice_recognizer._logging import getLogger, setup_logging
logger = getLogger(__name__)

# 请求的接口名
LFASR_HOST = "https://raasr.xfyun.cn/v2/api"
API_UPLOAD = "/upload"
API_GET_RESULT = "/getResult"

def _get_ts():
    '''
    获取调用时间戳。

    Returns:
      str: 当前时间的时间戳字符串。
    '''
    return str(int(time.time()))

def _get_signa(
    appid: str,
    secret_key: str,
    ts: str,
):
    '''
    获取调用签名。

    Args:
      appid (str): 应用 ID。
      secret_key (str): 密钥。
      ts (str): 时间戳。

    Returns:
      str: 根据 appid、secret_key 和时间戳生成的签名字符串。
    '''
    # 参考自调用示例
    m2 = hashlib.md5()
    m2.update((appid + ts).encode('utf-8'))
    md5 = m2.hexdigest()
    md5 = bytes(md5, encoding='utf-8')
    # 以secret_key为key, 上面的md5为msg,  使用hashlib.sha1加密结果为signa
    signa = hmac.new(secret_key.encode('utf-8'), md5, hashlib.sha1).digest()
    signa = base64.b64encode(signa)
    signa = str(signa, 'utf-8')
    return signa

def _result2sentence(
    orderResult: str
):
    '''
    将 API 识别结果转化为文本（取第一个结果, 不考虑多角色）。

    Args:
      orderResult (str): API 返回的 JSON 格式字符串，包含语音识别结果。

    Returns:
      str: 提取后的识别文本。
    '''

    sentence_list = []

    # orderResult 为 json 格式的字符串
    raw_json = dict(json.loads(orderResult))

    # 获取所有语句段落
    lattice_list = list(raw_json["lattice"])
    for lattice_raw in lattice_list:
        lattice_json = dict(json.loads(lattice_raw["json_1best"]))
        lattice_list = list(lattice_json["st"]["rt"][0]["ws"])
        # 提取各个识别字（提取第一个结果）
        for word_dict in lattice_list:
            sentence_list.append(word_dict["cw"][0]["w"])
        
    return "".join(sentence_list)

@dataclass
class RequestBodyXF:
    '''
    请求体数据类，用于封装语音识别接口所需参数。
    '''
    appid: str
    secret_key: str
    signa: str
    ts: str

    @classmethod
    def make(
        cls,
        appid: str,
        secret_key: str
    ):
        '''
        创建 RequestBodyXF 实例。

        Args:
          appid (str): 应用 ID。
          secret_key (str): 密钥。

        Returns:
          RequestBodyXF: 初始化后的实例。
        '''
        ts = _get_ts()
        signa = _get_signa(appid, secret_key, ts)
        return RequestBodyXF(appid, secret_key, signa, ts)

    def fresh(self):
        '''刷新时间戳与调用签名'''
        self.ts = _get_ts()
        self.signa = _get_signa(self.appid, self.secret_key, self.ts)

class Speach2TextXF:
    '''
    科大讯飞语音识别客户端类，提供上传音频文件、获取识别结果等功能。
    '''

    def __init__(
        self,
        rb: RequestBodyXF,
    ):
        '''
        初始化 Speach2TextXF 实例。

        Args:
          rb (RequestBodyXF): 请求体对象，包含 appid, secret_key, signa, ts。
        '''
        self.rb = rb

    def _upload(
        self,
        upload_audio_file: Union[str, Path],
        request_timeout: float = 2
    ):
        '''
        上传音频文件至科大讯飞服务器。

        Args:
          upload_audio_file (Union[str, Path]): 音频文件路径。
          request_timeout (float, optional): 请求超时时间（秒），默认为 2 秒。

        Returns:
          out (Optional[str]): 成功时返回订单号，失败时返回 None。
        '''
        logger.info("上传音频")

        if isinstance(upload_audio_file, str):
            upload_audio_file = Path(upload_audio_file)
        
        if not os.path.isfile(upload_audio_file):
            logger.error("上传文件不存在")
            return None

        file_len = os.path.getsize(upload_audio_file)
        file_name = os.path.basename(upload_audio_file)

        param_dict = {}
        param_dict['appId'] = self.rb.appid
        param_dict['signa'] = self.rb.signa
        param_dict['ts'] = self.rb.ts
        param_dict["fileSize"] = file_len
        param_dict["fileName"] = file_name
        param_dict["duration"] = "200"
        logger.debug("upload 参数：%s", param_dict)
        data = open(upload_audio_file, 'rb').read(file_len)

        try:
            response = requests.post(
                url = LFASR_HOST + API_UPLOAD,
                headers = {"Content-type":"application/json"},
                data = data,
                params = param_dict,
                timeout = request_timeout
            )
        except Exception as e:
            logger.error(f"API 请求失败: {e}")
            return None

        logger.debug("upload 链接: %s", response.request.url)
        result = dict(response.json())
        logger.debug("upload 响应: %s", result)

        try:
            orderId = str(result['content']['orderId'])
            logger.debug("上传成功, 返回订单号: %s", orderId)
            return orderId
        except Exception as e:
            logger.error(f"上传失败: {e}")
            return None

    def _get_result(
        self,
        orderId: str,
        request_timeout: float,
        try_interval: float,
        max_try_time: int,
    ):
        '''
        查询语音识别结果。

        Args:
          orderId (str): 订单号。
          request_timeout (float, optional): 请求超时时间（秒）。
          try_interval (float, optional): 查询间隔时间（秒）。
          max_try_time (int, optional): 最大尝试次数。

        Returns:
          out (Optional[str]): 成功时返回识别结果字符串，失败时返回 None。
        '''
        logger.info("查询结果")

        param_dict = {}
        param_dict['appId'] = self.rb.appid
        param_dict['signa'] = self.rb.signa
        param_dict['ts'] = self.rb.ts
        param_dict['orderId'] = orderId
        logger.debug("get result 参数: %s", param_dict)

        # 建议使用回调的方式查询结果, 查询接口有请求频率限制
        try_time = 0
        while True:
            try_time += 1
            logger.debug("请求尝试次数: %s", try_time)
            
            try:
                response = requests.post(
                    url = LFASR_HOST + API_GET_RESULT,
                    headers = {"Content-type": "application/json"},
                    params = param_dict,
                    timeout = request_timeout
                )
            except Exception as e:
                logger.error(f"API 请求失败: {e}")
                return None

            result = dict(response.json())
            logger.debug("请求结果: %s", result)
            status = result['content']['orderInfo']['status']
            logger.debug("请求状态: %s", status)

            if status == 4:
                orderResult = str(result['content']["orderResult"])
                logger.debug("语音转换完成, 得到结果: %s", orderResult)
                return orderResult
            elif status == -1:
                logger.error(f"语音转换失败, 失败代码: {result['content']['orderInfo']['failType']}")
                return None
            if try_time > max_try_time:
                logger.error("超过最大尝试次数")
                return None

            time.sleep(try_interval)

    @classmethod
    def exec(
        cls,
        appid: str,
        secret_key: str,
        upload_audio_file: Union[str, Path],
        request_timeout: float = 10,
        # 请求间隔, 根据音频大小适当加长
        try_interval: float = 3,
        max_try_time: int = 5,
    ):
        '''
        执行完整的语音识别流程：上传音频并获取结果。

        Args:
          appid (str): 应用 ID。
          secret_key (str): 密钥。
          upload_audio_file (Union[str, Path]): 音频文件路径。
          request_timeout (float, optional): 请求超时时间（秒），默认为 10 秒。
          try_interval (float, optional): 查询间隔时间（秒），默认为 3 秒。
          max_try_time (int, optional): 最大尝试次数，默认为 5 次。

        Returns:
          out (Optional[str]): 成功时返回识别后的文本，失败时返回 None。

        Todo:
          1. 暂未处理多角色识别的场景。
        '''
        req = Speach2TextXF(RequestBodyXF.make(
            appid, secret_key
        ))
        
        orderId = req._upload(
            upload_audio_file,
            request_timeout
        )
        if orderId is None:
            logger.error("音频上传失败")
            return None

        res = req._get_result(
            orderId,
            request_timeout,
            try_interval,
            max_try_time,
        )
        if res is None:
            logger.error("结果请求失败")
            return None
        
        result = _result2sentence(res)
        logger.info("语音识别完成, 得到结果: %s", result)
        return result

    @dataclass
    class Client:
        # 默认尝试从环境变量 XF_APP_ID 读取 appid
        appid: str = field(default_factory = lambda: os.environ.get('XF_APP_ID', "<appid>"))
        # 默认尝试从环境变量 XF_SECRET_KEY 读取 secret_key
        secret_key: str = field(default_factory = lambda: os.environ.get('XF_SECRET_KEY', "<secret_key>"))
        request_timeout: float = 10
        try_interval: float = 3
        max_try_time: int = 5

        def exec(
            self,
            upload_audio_file: Union[str, Path]
        ):
            '''
            执行语音转文本的请求。

            Args:
                upload_audio_file (Union[str, Path]): 要上传的音频文件路径。

            Returns:
                out (Optional[str]): 成功时返回识别后的文本，失败时返回 None。
            '''
            return Speach2TextXF.exec(
                self.appid,
                self.secret_key,
                upload_audio_file,
                self.request_timeout,
                self.try_interval,
                self.max_try_time
            )

if __name__ == "__main__":

    import tyro
    from dataclasses import dataclass
    dotenv.load_dotenv()

    @dataclass
    class Cfg:
        # 测试音频路径
        TEST_VOICE_PATH: str = Path(__file__).parent.joinpath("sample.mp3").as_posix()
        # 科大讯飞 app id
        XF_APP_ID = str(os.environ.get("XF_APP_ID"))
        # 科大讯飞 secret key
        XF_SECRET_KEY = str(os.environ.get("XF_SECRET_KEY"))

    setup_logging()
    cfg = tyro.cli(Cfg)

    # 测试代码
    res = Speach2TextXF.exec(
        cfg.XF_APP_ID,
        cfg.XF_SECRET_KEY,
        cfg.TEST_VOICE_PATH
    )
    print(f"语音识别结果: {res}")
