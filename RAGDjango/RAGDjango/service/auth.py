import secrets
import time

import redis
from django.http import JsonResponse  # 将数据以Json格式发送给前端
from langchain.agents import create_agent  # 创建智能体的库
from langgraph.checkpoint.memory import InMemorySaver  # 让大模型拥有记忆功能(内存记忆)
from pydantic import BaseModel, Field

from ..llm import ChatModel
from ..tools.tools import send_email, smtp_send, sql_query

# redis的默认值;decode_responses=True 让 get() 直接返回 str,不用再 .decode()
# socket_connect_timeout:本机没装 Redis 时快速失败,别让一个请求卡好几秒
redis_conn = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True,
                         socket_connect_timeout=1)

# 验证码有效期(秒)
CODE_TTL = 300

# ---------- 验证码存取的统一入口:优先 Redis,本机没起 Redis 时退化成进程内存 ----------
# 原来直接调 redis_conn.set/get,一旦 Redis 没装就会在"邮件已经发出去"之后抛
# ConnectionError -> 500,用户收得到信却登不了录。这里只加一层兜底,
# 键名(login:code:邮箱)和 5 分钟有效期这两个语义完全不变。
_memory_codes = {}  # {key: (code, 过期时间戳)} — 仅 Redis 不可用时使用


def _code_set(key, code):
    try:
        redis_conn.set(key, code, ex=CODE_TTL)
    except redis.RedisError as e:
        print(f"[cache] Redis 不可用,验证码先存进程内存(重启失效): {e}")
        _memory_codes[key] = (code, time.time() + CODE_TTL)


def _code_get(key):
    try:
        return redis_conn.get(key)
    except redis.RedisError:
        item = _memory_codes.get(key)
        if not item:
            return None
        code, expires = item
        if time.time() > expires:  # 内存兜底也要遵守 5 分钟有效期
            _memory_codes.pop(key, None)
            return None
        return code


def _code_delete(key):
    try:
        redis_conn.delete(key)
    except redis.RedisError:
        _memory_codes.pop(key, None)


# ============================================================
# 一、默认流程:不校验邮箱是否注册,直接生成验证码并发邮件
#    (纯 Python 实现,不经过大模型:快、稳定、验证码不会编错)
# ============================================================

def generate_code() -> str:
    """生成 6 位随机数字验证码

    用 secrets 而不是 random:random 是可预测的伪随机数,不适合做验证码。
    """
    return f"{secrets.randbelow(1_000_000):06d}"


def build_code_email_html(code: str) -> str:
    """验证码邮件正文(HTML 模板)

    用 __CODE__ 占位再 replace,而不是 f-string:因为模板里全是 CSS 的 { },
    用 f-string 会把 CSS 花括号当成占位符,直接报 KeyError/语法错。
    """
    return """<!DOCTYPE html>
<html>
<body style="margin:0;padding:24px;background:#f4f6fb;font-family:-apple-system,'Microsoft YaHei',sans-serif;">
  <div style="max-width:520px;margin:0 auto;background:#ffffff;border-radius:14px;overflow:hidden;
              box-shadow:0 6px 24px rgba(31,41,55,.08);">
    <div style="background:linear-gradient(135deg,#4f7cff,#7b5cff);padding:26px 28px;color:#ffffff;">
      <div style="font-size:18px;font-weight:600;">🔐 登录验证码</div>
      <div style="font-size:13px;opacity:.85;margin-top:6px;">RAGDjango 邮箱登录</div>
    </div>
    <div style="padding:28px;">
      <p style="margin:0 0 18px;color:#374151;font-size:14px;">您好，本次登录的验证码为：</p>
      <div style="text-align:center;font-size:34px;font-weight:700;letter-spacing:10px;color:#4f7cff;
                  background:#eef2ff;border-radius:10px;padding:16px 0;">__CODE__</div>
      <p style="margin:18px 0 0;color:#6b7280;font-size:13px;line-height:1.7;">
        验证码 <b>5 分钟</b> 内有效，请勿泄露给他人。<br>如非本人操作，请忽略本邮件。
      </p>
    </div>
  </div>
</body>
</html>""".replace("__CODE__", code)


def send_email_assistant(email):
    """发送登录验证码:任何邮箱都可以发,不查 users 表"""
    email = (email or "").strip().lower()
    if not email:
        return JsonResponse({"code": 400, "msg": "邮箱地址不能为空！", "data": ""})

    code = generate_code()
    subject = f"【登录验证码】{code}（5 分钟内有效）"

    ok, err = smtp_send(email, subject, build_code_email_html(code))
    if not ok:  # 邮件没发出去就别存 redis,否则用户永远收不到码
        print(f"[send_code] 邮件发送失败 -> {email}: {err}")
        # 不把 SMTP 原始报文甩给前端,只把常见原因翻译成人话
        if "550" in err or "recipient" in err.lower():
            msg = "邮件发送失败,该邮箱地址可能不存在,请检查后重试！"
        else:
            msg = "邮件发送失败,请稍后重试！"
        return JsonResponse({"code": 500, "msg": msg, "data": ""})

    # 邮件发送成功后才写入缓存,有效期 CODE_TTL 秒
    _code_set(f"login:code:{email}", code)
    print(f"[send_code] 验证码已发送 -> {email}")
    # 验证码只发到邮箱,绝对不要回传给浏览器
    return JsonResponse({"code": 200, "msg": "验证码发送成功！", "data": ""})


# 访问前端登录页面
def login_code(account, code):
    account = (account or "").strip().lower()
    code = str(code or "").strip()
    if not account or not code:
        return JsonResponse({"code": 400, "msg": "邮箱和验证码不能为空！"})

    key = f"login:code:{account}"
    stored = _code_get(key)  # decode_responses=True,直接返回 str 或 None
    if stored and stored == code:
        _code_delete(key)  # 验证码一次性使用,登录成功立即失效
        return JsonResponse({"code": 200, "msg": "正在登录!"})
    return JsonResponse({"code": 500, "msg": "验证码过期或错误!"})


# ============================================================
# 二、备用流程:大模型 Agent 版(会产生 sql_query 查库 + 模型编造验证码的问题)
#    想让大模型来做,把 views.send_code 改成调用 send_email_assistant_by_agent 即可。
#    注意:这条链路会去查 users 表,库里没有的邮箱会被判成"邮箱未注册"而发不出码。
# ============================================================

# 初始化记忆功能
memory = InMemorySaver()


class EmailResp(BaseModel):
    """大模型结构化输出的规范

    注意: 字段名必须与提示词里约定的 key 完全一致(提示词用 data,这里就不能写 dats),
    否则下面取 ans["data"] 时会 KeyError。code 用 int,才能和 200 正确比较。
    """

    code: int = Field(..., description="状态码: 200 成功, 400 邮箱未注册, 500 发送失败")
    data: str = Field(default="", description="验证码,失败时为空字符串")
    msg: str = Field(..., description="提示信息")


def send_email_assistant_by_agent(email):
    """（备用）让大模型走 Agent:查 users 表 -> 生成验证码 -> 调用 send_email 工具"""
    email = (email or "").strip().lower()
    if not email:
        return JsonResponse({"code": 400, "msg": "邮箱地址不能为空！", "data": ""})

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
        tools=[send_email, sql_query],
        checkpointer=memory,
        response_format=EmailResp,
    )

    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": email}]},
            {"configurable": {"thread_id": email}},
        )
        ans = result["structured_response"].model_dump()
    except Exception as e:
        print(f"[send_code/agent] 智能体调用失败: {type(e).__name__}: {e}")
        return JsonResponse({"code": 500, "msg": f"服务器错误,请稍后重试！({type(e).__name__})", "data": ""})

    print("[send_code/agent] 模型返回:", ans)

    code = int(ans.get("code") or 0)
    verify_code = str(ans.get("data") or "").strip()

    if code == 200 and len(verify_code) == 6:
        redis_conn.set(f"login:code:{email}", verify_code, ex=CODE_TTL)
        return JsonResponse({"code": 200, "msg": ans.get("msg") or "验证码发送成功！", "data": ""})

    if code in (400, 500):
        msg = ans.get("msg") or ("邮箱未注册！" if code == 400 else "邮件发送失败！")
    else:
        code = 500
        msg = "验证码生成异常,请稍后重试！"
    return JsonResponse({"code": code, "msg": msg, "data": ""})
