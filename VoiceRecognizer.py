import os
from pathlib import Path
from typing import Union

import dotenv
from VoiceRecorder import VoiceRecorder
from Speach2TextXF import Speach2TextXF
from dataclasses import dataclass, field

from omegaconf import OmegaConf
import logging

@dataclass
class VoiceRecognizer:

    vr_clt: VoiceRecorder = field(default_factory = VoiceRecorder)
    sst_clt: Speach2TextXF.Client = field(default_factory = Speach2TextXF.Client)

    def record_recognize(
        self,
        tmp_voice_path: str = "tmp.wav"
    ):
        self.vr_clt.record_wav(tmp_voice_path)
        return self.sst_clt.exec(tmp_voice_path)

    @classmethod
    def from_cfg(
        cls,
        cfg_path: Union[str, Path]
    ):
        base_cfg = OmegaConf.structured(cls)
        yaml_cfg = OmegaConf.load(cfg_path)
        mix_cfg = OmegaConf.merge(base_cfg, yaml_cfg)
        
        res = OmegaConf.to_object(mix_cfg)
        assert isinstance(res, cls), f"类型 {type(res)} 与 {cls.__name__} 不匹配"
        return res

if __name__ == "__main__":

    # logger 设置
    logger = logging.getLogger(None)
    ch = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s|%(levelname)s|%(name)s:%(lineno)d|%(funcName)s: %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.setLevel(logging.DEBUG)

    # 测试代码
    dotenv.load_dotenv()
    XF_APP_ID = str(os.environ.get("XF_APP_ID"))
    XF_SECRET_KEY = str(os.environ.get("XF_SECRET_KEY"))
    TEST_VOICE_PATH = str(os.environ.get("TEST_VOICE_PATH"))

    obj = VoiceRecognizer.from_cfg("voice_recognize.yaml")
    print(obj.record_recognize())
