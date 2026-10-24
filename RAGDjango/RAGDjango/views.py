import json
import re

from django.http import JsonResponse  # 将数据以Json格式发送给前端
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from langchain.agents import create_agent
from sqlalchemy import false

from llm import ChatModel
from tools.tools import sql_query
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
def login_html(request):
    return render(request=request, template_name="login.html")


def index_html(request):
    return render(request, template_name="index.html")


# 兼容旧入口:邮件发送助手(question 即邮箱地址)
def send_email_assistant(request):
    email = (request.GET.get("question") or "").strip()
    return auth.send_email_assistant(email)


# 发送验证码的视图
@csrf_exempt
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
@csrf_exempt
@require_POST
def login_code(request):
    data = _parse_json_body(request)
    if data is None:
        return JsonResponse({"code": 400, "msg": "请求格式错误,需要 JSON 对象！"})

    email = (data.get("email") or "").strip()  # data["email"]
    code = data.get("code")
    print("[login_code] 收到:", {"email": email, "code": code})
    return auth.login_code(email, code)

# 定义生成器,模拟流式输出(SSE数据流)
"""
SSE格式:
data:我是
data:YOLO,请问
data:有什么可以帮你的?
"""
def see_generation(generator_func):
    try:
        for chunk in generator_func:
            if chunk: #当chunk存在时,构建SSE数据流 data:{"我是"\n\n}
                yield f"data:{json.dumps({"text":chunk},ensure_ascii=False)}\n\n"
    except Exception as e:
        yield f"data:{json.dumps({"error":str(e)},ensure_ascii=False)}\n\n"
    finally:
        yield "data:[DONE]\n\n"

        rag_store = {} #字典,存对话内容,存储RAG对话内容
        chat_store = {} #字典,存用户对话数据

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
            model = llm,
            system_prompt= prompt,
            tools=[send_email,sql_query],
            checkpointer=memory,
            debug=True,
        )

        def gene
