import json
import re

import memory
from django.db.migrations import questioner
from django.http import JsonResponse, StreamingHttpResponse  # 将数据以Json格式发送给前端
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_POST
from langchain.agents import create_agent
from langchain_classic.agents import agent
from langchain_classic.memory import prompt
from langchain_core.chat_history import InMemoryChatMessageHistory

# llm.py / tools/ 都在本包内,必须用相对导入(和 service/auth.py 里的写法一致)
from .llm import ChatModel
from .tools.tools import sql_query
from .service import auth

# 简单的邮箱格式校验(前端已经校验过一次,后端必须再校验一次)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _parse_json_body(request):
    """把请求体解析成 dict,失败返回 None(避免 json.loads 抛异常直接 500)"""
    try:
        data = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


# 访问前端登录页面
@ensure_csrf_cookie  # 保证这个页面一定下发 csrftoken cookie,前端后面的 POST 才带得上
def login_html(request):
    return render(request=request, template_name="login.html")


@ensure_csrf_cookie  # 同上:index 页也要有 csrftoken cookie
def index_html(request):
    return render(request, template_name="index.html")


# 兼容旧入口:邮件发送助手(question 即邮箱地址,GET 传参)
def send_email_assistant(request):
    email = (request.GET.get("question") or "").strip()
    return auth.send_email_assistant(email)


# ============================================================
# 流式邮件接口:POST /api/email/
#   这里故意【不加】@csrf_exempt —— CSRF 校验是开着的,
#   前端从 csrftoken cookie 里取出 token,放进 X-CSRFToken 头带回来。
# ============================================================
@require_POST
def email_assistant(request):
    data = _parse_json_body(request)
    if data is None:
        return JsonResponse({"code": 400, "msg": "请求格式错误,需要 JSON 对象！", "data": ""})

    # 前端发的是 {question: "邮箱地址", sessionId: "..."}
    email = (data.get("question") or "").strip()

    return StreamingHttpResponse(
        see_generation(send_code_chunks(email)),
        content_type="text/event-stream",
    )


def send_code_chunks(email):
    """把"发验证码"的过程拆成一段段文本,交给 see_generation 包装成 SSE

    真正发信复用 auth.send_email_assistant(纯 Python 那条链路,不经过大模型),
    这样验证码不会编错,也不会因为查库把已注册用户判成未注册。
    """
    email = (email or "").strip().lower()

    if not email:
        yield "邮箱地址不能为空！"
        return
    if not EMAIL_RE.match(email):
        yield "邮箱格式不正确！"
        return

    yield f"正在向 {email} 发送登录验证码…\n\n"

    payload = json.loads(auth.send_email_assistant(email).content)
    if payload.get("code") == 200:
        yield f"✅ {payload.get('msg') or '验证码发送成功！'}"
    else:
        yield f"❌ {payload.get('msg') or '验证码发送失败！'}"


# 发送验证码的视图
# (不再 @csrf_exempt:登录页会带 X-CSRFToken,校验交给中间件)
@require_POST
def send_code(request):
    data = _parse_json_body(request)
    if data is None:
        return JsonResponse({"code": 400, "msg": "请求格式错误,需要 JSON 对象！", "data": ""})

    email = (data.get("email") or "").strip()
    if not email:
        return JsonResponse({"code": 400, "msg": "邮箱地址不能为空！", "data": ""})
    if not EMAIL_RE.match(email):
        return JsonResponse({"code": 400, "msg": "邮箱格式不正确！", "data": ""})

    return auth.send_email_assistant(email)


# 验证码登录
@require_POST
def login_code(request):
    data = _parse_json_body(request)
    if data is None:
        return JsonResponse({"code": 400, "msg": "请求格式错误,需要 JSON 对象！"})

    email = (data.get("email") or "").strip()  # data["email"]
    code = data.get("code")
    print("[login_code] 收到:", {"email": email, "code": code})
    return auth.login_code(email, code)

# 会话级内存存储(模块级,跨请求复用)
# 说明:这两个字典原来写在 see_generation 的 finally 里、位于 yield 之后,
# 是永远不会执行到的死代码;现在挪到模块顶层,api_chat 才能按 sessionId 取到历史。
rag_store = {}   # 字典,存 RAG 对话内容
chat_store = {}  # 字典,存用户对话数据 {sessionId: InMemoryChatMessageHistory}


# 定义生成器,模拟流式输出(SSE数据流)
"""
SSE格式:
data:{"text":"我是"}
data:{"text":"YOLO,请问"}

注意 "data:" 后面统一带一个空格(标准 SSE 写法),前端两种写法都能解析。
"""


def sse_frame(payload: dict) -> str:
    """拼一帧 SSE。统一在这里加空格,别再各写各的。"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def see_generation(generator_func):
    try:
        for chunk in generator_func:
            if chunk:  # 当chunk存在时,构建SSE数据流
                yield sse_frame({"text": chunk})
    except Exception as e:
        yield sse_frame({"error": str(e)})
    finally:
        yield "data:[DONE]\n\n"

@csrf_exempt
@require_POST
def send_email_assis(request):
    data = json.loads(request.body)
    question = data.get("question")
    seessionId = data.get("seessionId")
    llm = ChatModel.load_model_once()
    prompt = """
            一、你是一个验证码发送助手，你有2个工具：
                1: sql_query：执行SQL语句查询数据库
                2: send_email：执行邮件发送
            二、工具流程：必须严格按照以下流程进行工作
                步骤一：根据用户输入的信息（邮箱地址），构造相应的查询条件。
                步骤二：调用 sql_query 工具，查询 users 表中是否存在该用户信息及其邮箱。
                步骤三：如果用户存在且邮箱不为空，那么就必须先生成随机6位数的验证码。
                步骤四：将获取到的验证码作为参数，调用 send_email 工具发送邮件。
            三、反馈信息规范
                1. 如果 sql_query 查询结果为空，请返回：{"code": 400, "msg": "邮箱未注册！", "data": ""}
                2. 如果 send_email 发送成功，请返回：{"code": 200, "msg": "验证码发送成功！", "data": "生成的验证码"}
                3. 如果 send_email 发送失败，请返回：{"code": 500, "msg": "邮件发送失败！", "data": ""}
        """

    agent = create_agent(
        model=llm,
        system_prompt=prompt,
        tools=[send_email_assis, sql_query],
        checkpointer=memory,
        debug=True,
    )

def generate():
    for chunk,metadata in agent.stream(
            {"messages":[{"role":"user","content":questioner}]},
            {"configuable":{"thread_id":0}},
        stream_mode="message"
    ):
        print("=====================")
        print(chunk,metadata)
        if chunk.content and not getattr(chunk,"tool_calls",None):
            yield chunk.content

        return StreamingHttpResponse(see_generation(generate()),content_type="text/event-stream")

# 基础聊天功能
# (按方案 C 统一走 CSRF 校验,前端会带 X-CSRFToken)
@require_POST
def api_chat(request):
    data = _parse_json_body(request)
    if data is None:
        return JsonResponse({"code": 400, "msg": "请求格式错误,需要 JSON 对象！", "data": ""})

    question = (data.get("question") or "").strip()
    sessionId = data.get("sessionId")
    llm = ChatModel.load_model_once()

    # 判断是否已经存在历史信息(按 sessionId 隔离,同一个用户的多轮对话共享上下文)
    if sessionId not in chat_store:
        chat_store[sessionId] = InMemoryChatMessageHistory()
    history = chat_store[sessionId]

    from langchain_core.messages import HumanMessage

    def generate():
        full_response = ""
        # 将历史信息和当前用户信息，一起发送给大模型
        messages = history.messages + [HumanMessage(content=question)]
        # 流式输出:每读到一段就 yield 出去,前端才能边收边显示
        for chunk in llm.stream(messages):
            if chunk.content:
                full_response += chunk.content
                yield chunk.content
        # 流结束后再写入历史,保证存进 chat_store 的是完整回复
        history.add_user_message(question)
        history.add_ai_message(full_response)

    return StreamingHttpResponse(see_generation(generate()), content_type="text/event-stream")


# RAG 法律问答:检索那部分还没写,先给一句明确提示,避免默认模式直接 404
@require_POST
def api_rag(request):
    return StreamingHttpResponse(
        see_generation(iter(["RAG 法律问答还没接入知识库检索，可以先用「基础聊天」模式。"])),
        content_type="text/event-stream",
    )