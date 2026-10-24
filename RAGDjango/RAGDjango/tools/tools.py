import os
import smtplib
from email.mime.text import MIMEText

import MySQLdb
from langchain_core.tools import tool  # 必须导入 tool 才能使用 @tool 装饰器
from pydantic import BaseModel, Field

# ---- 邮件账号配置:优先读环境变量,避免密码写死在代码里被 git 带走 ----
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.qq.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "3777057642@qq.com")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "drccvhkonolocbif")

# ---- MySQL 配置 ----
MYSQL_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),  # 链接本地地址
    "port": int(os.environ.get("MYSQL_PORT", "3306")),  # 数据库端口号
    "user": os.environ.get("MYSQL_USER", "root"),  # 数据库用户
    "password": os.environ.get("MYSQL_PASSWORD", "123456"),  # 数据库密码
    "database": os.environ.get("MYSQL_DATABASE", "rag"),  # 连接的数据库
    "charset": "utf8mb4",  # 编码方案,utf8mb4允许输出某些emoji
}


# 定义邮件需要接受的参数(大模型生成)
class EmailSchema(BaseModel):
    to: str = Field(..., description="收件人邮箱地址")  # ...表示这是一个必须参数
    subject: str = Field(..., description="邮箱主题")
    content: str = Field(..., description="邮件正文")


def smtp_send(to: str, subject: str, content: str):
    """真正的发信实现(普通函数)

    视图里直接调用它就够了,不需要经过大模型;
    @tool 装饰的 send_email 只是把它包一层给 Agent 用。
    返回 (是否成功, 错误信息)
    """
    smtp = None
    try:
        text = MIMEText(content, "html", "utf-8")  # 创建邮箱发送对象(必须指定utf-8编码,否则中文乱码)
        # 注意: 赋值语句结尾不能加逗号,否则会赋值成元组("a@b.com",),
        # 元组没有.encode()方法,就会报 'tuple' object has no attribute 'encode'
        text["to"] = to
        text["subject"] = subject
        text["from"] = SMTP_USER

        # 创建SMTP邮箱对象
        smtp = smtplib.SMTP_SSL(host=SMTP_HOST, port=SMTP_PORT, timeout=15)  # 通过SSL密钥连接服务器
        smtp.login(user=SMTP_USER, password=SMTP_PASSWORD)
        smtp.sendmail(SMTP_USER, to, text.as_string())
        return True, ""
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"
    finally:
        if smtp is not None:
            try:
                smtp.quit()
            except Exception:
                pass


# 定义一个智能体工具(供大模型执行对应功能)
@tool("send_email", args_schema=EmailSchema)
def send_email(to: str, subject: str, content: str) -> str:
    """
    发送邮件
    """
    ok, err = smtp_send(to, subject, content)
    return f"邮件成功发送给{to}!" if ok else f"邮件发送失败,失败原因{err}"


"""
数据库查询工具
"""


class SQLSchema(BaseModel):
    sql: str = Field(..., description="数据库查询语句")


@tool("sql_query", args_schema=SQLSchema)
def sql_query(sql: str) -> str:
    """
    执行SQL查询语句
    """
    con = None
    cursor = None
    try:
        con = MySQLdb.connect(connect_timeout=5, **MYSQL_CONFIG)  # 数据库链接对象,配置数据库参数
        cursor = con.cursor()  # 创建游标连接数据库
        cursor.execute(sql)  # 执行SQL语句
        result = cursor.fetchall()  # 获取执行结果
        return str(result)
    except Exception as e:
        return f"数据库查询失败,失败原因{e}"
    finally:  # 无论成功失败都要关闭连接,否则连接会越积越多
        if cursor is not None:
            cursor.close()
        if con is not None:
            con.close()
