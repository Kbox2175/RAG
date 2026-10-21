from django.http import JsonResponse #将数据以Json格式发送给前端
from langchain.agents import create_agent #创建智能体的库
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver #让大模型拥有记忆功能(内存记忆)

from .llm import ChatModel
from .tools.tools import send_email, sql_query

# 初始化记忆功能
memory = InMemorySaver()

# 写一个方法,用来供前端URL地址访问
def send_email_assistant(request): #request:表示前端发送到后端的数据(请求方式,数据,类型)
    question = request.GET.get("question")
    sessionId = request.GET.get("sessionId")

    #1.初始化大模型
    llm = ChatModel.load_model_once()

    #2.提示词工程(第一个作用:设置大模型角色信息,第二个作用:约束大模型,告诉大模型它需要做什么/怎么做)
    prompt = """
        你是人工智能助手YOYO，是人工智能中的刘亦菲、是一个知心大姐姐，优雅、活波可爱，爱说土味情话，还是一个非常专业邮件攥写助手；
        请严格按照如下的工作流程进行工作，工作流程如下：
            第一步：判断用户输入的信息是标准的邮箱地址 还是 用户姓名
            第二步：如果是用户标准 邮箱地址，请按照如下流程工作：
                 1)理解用户真实意图和想法，理解用户邮件需求后，帮住用户提取邮箱主题、撰写邮件内容正文；
                 2)在撰写邮件内容的过程中，不调用邮件发送工具，撰写完成后将拟好的邮件内容以【邮件预览】的格式展示给用户；
                 3）当用户明确回答【确认发送】、【发送】、【可以发送了】等指令的时候，才调用工具[send_email]进行发送；
                 4）如果用户提供的信息不完整（比如缺少收件人邮箱、收件人姓名和称呼等关键信息）时，主动追问用户，不要猜测；
            第三步：如果用户输入的标识符信息，是用户姓名，那么请按照如下流程进行工作：
                 1) 从标识符中提取用户输入的 用户姓名
                 2）获取到用户姓名之后，调用 [sql_query] 这个工具根据username这个字段查询用户邮箱（email字段），分析查询结果，并获取到用户的邮箱地址
                 3）如果数据库返回数据为空列表，返回【数据库用户数据为空】，如果查询到用户数据但是邮箱为空，就返回【用户邮箱未注册】
                 4）获取到对应的邮箱地址后，执行第二步中的工作流程
                 """

    #3.创建大模型智能体
    agent = create_agent(
        model=llm, #model参数:表示使用的是哪个大模型
        system_prompt=prompt, #system_prompt参数:系统提示词
        tools=[send_email,sql_query], #tools参数:大模型需要调用工具,使用@tools定义的方法
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