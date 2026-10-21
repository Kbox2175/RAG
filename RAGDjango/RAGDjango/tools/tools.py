import smtplib
from email.mime.text import MIMEText

from langchain_core.tools import tool  # 必须导入 tool 才能使用 @tool 装饰器
from pydantic import BaseModel, Field


# 定义邮件需要接受的参数(大模型生成)
class EmailSchema(BaseModel):
    to:str = Field(...,description="收件人邮箱地址") # ...表示这是一个必须参数
    subject:str = Field(...,description="邮箱主题")
    content:str = Field(...,description="邮件正文")


# 定义一个智能体工具(供大模型执行对应功能)
def send_email(to: str, subject: str, content: str):
    """
    发送邮件
    """
    try:
        text = MIMEText(content, "plain", "utf-8") # 创建邮箱发送对象(必须指定utf-8编码,否则中文乱码)
        # 注意: 赋值语句结尾不能加逗号,否则会赋值成元组("a@b.com",),
        # 元组没有.encode()方法,就会报 'tuple' object has no attribute 'encode'
        text["to"] = to
        text["subject"] = subject
        text["from"] = "3777057642@qq.com"

        # 创建SMTP邮箱对象
        smtp = smtplib.SMTP_SSL(host = "smtp.qq.com", port = 465) #通过SSL密钥连接服务器
        smtp.login(user = "3777057642@qq.com", password = "drccvhkonolocbif")
        smtp.sendmail("3777057642@qq.com",to,text.as_string())
        smtp.quit()
        return f"邮件成功发送给{to}!"

    except Exception as e:
        return f"邮件发送失败,失败原因{e}"


"""
数据库查询工具
"""

import MySQLdb
class SQLSchema(BaseModel):
    sql:str = Field(...,description="数据库查询语句")

@tool("sql_query",args_schema=SQLSchema)
def sql_query(sql:str):
    """
    执行SQL查询语句
    """
    try:
        con = MySQLdb.connect( #数据库链接对象,配置数据库参数
            host = "localhost", # 链接本地地址
            port = 3306, # 数据库端口号
            user = "root", # 数据库用户
            password = "123456", # 数据库密码
            database = "rag", # 连接的数据库
            charset = "utf8mb4", # 编码方案,utf8mb4允许输出某些emoji
        )
        cursor = con.cursor() #创建游标连接数据库
        cursor.execute(sql) #执行SQL语句
        result = cursor.fetchall() #获取执行结果
        cursor.close() #关闭游标
        con.close() #关闭连接对象
        return str(result)
    except Exception as e :
        return f"数据库查询失败,失败原因{e}"