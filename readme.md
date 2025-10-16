# 语音识别功能模块

使用科大讯飞 API 实现语音识别功能。

## 代码结构

- `Speach2TextXF.py` 实现语音转文字功能
- `VoiceRecorder.py` 实现语音录制功能
- `VoiceRecognizer.py` 整合两个模块实现语音识别并转文字

## 使用说明

在[科大讯飞控制台](https://console.xfyun.cn/services/lfasr)获取 `APPID` 与 `SecretKey` 后通过以下方式之一载入
- 将 `APPID` 与 `SecretKey` 分别载入环境变量 `XF_APP_ID` 与 `XF_SECRET_KEY`
- 将 `APPID` 与 `SecretKey` 写入配置文件的键 `sst_clt.app_id` 与 `sst_clt.secret_key`

## 参考代码

使用[科大讯飞录音文件转写标准版](https://www.xfyun.cn/services/lfasr?ch=xfow)（实名认证后第一年免费）
- 控制台创建应用，领取免费语音转写，在应用工作台查看 APPID 与 SecretKey
- 不使用科大讯飞 SDK，而是直接 request 调用相关 API，[文档](https://www.xfyun.cn/doc/asr/ifasr_new/API.html#%E6%8E%A5%E5%8F%A3%E8%A6%81%E6%B1%82)，[示例 Demo](https://xfyun-doc.xfyun.cn/static/16735945125044764/lfasr_new_python_demo.zip)

获取麦克风音频
- [机器人语音录制示例](https://github.com/dehaozhou/Dehao-Zhou/blob/main/%E5%88%A9%E7%94%A8%E5%A4%9A%E6%A8%A1%E6%80%81%E6%A8%A1%E5%9E%8BQwen2.5-VL%E7%90%86%E8%A7%A3%E4%BA%BA%E7%B1%BB%E6%84%8F%E5%9B%BE%EF%BC%8C%E8%BF%9B%E8%A1%8C%E4%BA%A4%E4%BA%92%E5%BC%8F%E6%8A%93%E5%8F%96/vlm_process.py)
