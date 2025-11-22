import os
from pathlib import Path
from typing import Union

import dotenv
from voice_recognizer.VoiceRecorder import VoiceRecorder
from voice_recognizer.Speach2TextXF import Speach2TextXF
from dataclasses import dataclass, field

from omegaconf import OmegaConf
from voice_recognizer._logging import setup_logging

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

    import tyro
    from dataclasses import dataclass
    dotenv.load_dotenv()

    @dataclass
    class Cfg:
        # 识别器配置文件路径
        voice_recognize_cfg_path: str = Path(__file__).parent.joinpath("voice_recognize.yaml").as_posix()
        
    setup_logging()
    cfg = tyro.cli(Cfg)
    
    # 测试代码
    obj = VoiceRecognizer.from_cfg(cfg.voice_recognize_cfg_path)
    print(obj.record_recognize())
