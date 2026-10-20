from django.http import JsonResponse #将数据以Json格式发送给前端
from langchain.agents import create_agent #创建智能体的库
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver #让大模型拥有记忆功能(内存记忆)
from .llm import ChatModel
from .tools.tools import send_email

# 初始化记忆功能
memory = InMemorySaver()

# 写一个方法,用来供前端URL地址访问
def send_email_assistant(request): #request:表示前端发送到后端的数据(请求方式,数据,类型)
    question = request.GET.get("question")
    sessionId = request.GET.get("sessionId")

    #1.初始化大模型
    llm = ChatModel.load_model_once()

    #2.提示词工程(第一个作用:设置大模型角色信息,第二个作用:约束大模型,告诉大模型它需要做什么/怎么做)
    prompt = """..."""

    #3.创建大模型智能体
    agent = create_agent(
        model=llm, #model参数:表示使用的是哪个大模型
        system_prompt=prompt, #system_prompt参数:系统提示词
        tools=[send_email], #tools参数:大模型需要调用工具,使用@tools定义的方法
        checkpointer=memory,
        debug=True
    )

    #4.调用智能体
    result = agent.invoke(
        {"messages":[{"role":"user","content":question}]},
        RunnableConfig(configurable={"thread_id":sessionId}) #sessionId用户标识:隔离用户对话
    )
    print(result["messages"][-1].content)
    return JsonResponse({"result":result["messages"][-1].content})