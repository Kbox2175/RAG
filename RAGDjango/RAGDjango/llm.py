import os
import threading

from langchain_openai import ChatOpenAI

# 密钥不要写死在代码里(会跟着 git 提交泄露),放到环境变量里:
#   Windows: setx DASHSCOPE_API_KEY "sk-xxx"   然后重开终端
# 这里的默认值只是为了你本地还能直接跑起来。
DEFAULT_API_KEY = "sk-ws-H.PYHEMPE.74U6.MEUCIQD9f2J08dtvP8EVcgtbJZ5MLefhzDyqQhq2Rye_4XTw8AIgP-Un-QBSfjjvg9oE7mz-sVhq3JH_dFZxAbt5Y_58x7A"


class ChatModel:
    # 定义类变量(存储初始化后的模型)
    _model = None

    # 定义线程锁(初始化后给变量上死锁)
    _lock = threading.Lock()

    # 定义类方法,用于初始化大模型
    @classmethod
    def load_model_once(cls):
        if cls._model is None:
            with cls._lock:
                # 双重检查:等锁期间可能已被别的线程初始化好了
                if cls._model is None:
                    cls._model = ChatOpenAI(
                        model="qwen3.8-flash",
                        api_key=os.environ.get("DASHSCOPE_API_KEY", DEFAULT_API_KEY),
                        base_url="https://ws-dd56sevw5o7x58j9.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
                        temperature=0.8,
                        extra_body={"thinking": {"type": "disabled"}},
                    )
        return cls._model


if __name__ == '__main__':
    llm = ChatModel.load_model_once()
    result = llm.invoke("你是谁")
    print(result)
