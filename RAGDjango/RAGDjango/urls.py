"""
URL configuration for RAGDjango project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconfig
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path

from .views import index_html, login_code, login_html, send_code, send_email_assistant

# path路由地址,前端访问的URL请求地址,比如www.baidu.com/图片
# 路由的语法格式:path("请求路径/",views中的将要访问的方法,name="就是这个路由的名称")
# 如果在前端访问路由执行对应的方法:启动服务器127.0.0.1:8000/请求路径?形参变量--后端需要接收的值


def ignore_browser_probe(request, rest=None):
    """浏览器统计类插件会乱发 /hybridaction/zybTrackerStatisticsAction 这类请求,
    与本项目无关(不是路由写错)。返回 204 让日志干净,不用管它。
    想恢复原本的 404 提示,删掉下面这条 path 即可。"""
    return HttpResponse(status=204)


urlpatterns = [
    path('admin/', admin.site.urls),
    path("send_email/", send_email_assistant, name="邮件发送助手"),
    path("", login_html, name="访问登陆页面!"),  # "":默认请求地址,localhost:8000
    path("send_code/", send_code, name="验证码发送!"),
    path("index/", index_html, name="主页页面"),
    path("login_code/", login_code, name="验证码登录功能!"),
    path("hybridaction/<path:rest>", ignore_browser_probe),
    path("api/email/",send_email_assis,name="流式输出邮件"),
]
