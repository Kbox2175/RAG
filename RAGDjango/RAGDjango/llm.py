from langchain_openai import ChatOpenAI
import threading

# 创建一个类

class ChatModel:
    # 定义类变量(存储初始化后的模型)
    _model = None

    # 定义线程锁(初始化后给变量上死锁)
    _lock = threading.Lock()

    #定义类方法,用于初始化大模型
    @classmethod
    def load_model_once(cls):
        if cls._model is None:
            with cls._lock:
                cls._model = ChatOpenAI(
                    model="qwen3.8-flash",
                    api_key="sk-ws-H.PYHEMPE.74U6.MEUCIQD9f2J08dtvP8EVcgtbJZ5MLefhzDyqQhq2Rye_4XTw8AIgP-Un-QBSfjjvg9oE7mz-sVhq3JH_dFZxAbt5Y_58x7A",
                    base_url="https://ws-dd56sevw5o7x58j9.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
                    temperature=0.8,
                )
        return cls._model

if __name__ == '__main__':
    llm = ChatModel.load_model_once()
    result = llm.invoke("你是谁")
    print(result)