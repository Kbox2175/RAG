import smtplib
from email.mime.text import MIMEText

from langchain_core import tools
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
