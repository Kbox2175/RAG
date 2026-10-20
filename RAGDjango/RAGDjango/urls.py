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
from django.urls import path

from .views import *
# path路由地址,前端访问的URL请求地址,比如www.baidu.com/图片
# 路由的语法格式:path("请求路径/",views中的将要访问的方法,name="就是这个路由的名称")
# 如果在前端访问路由执行对应的方法:启动服务器127.0.0.1:8000/请求路径?形参变量--后端需要接收的值

urlpatterns = [
    path('admin/', admin.site.urls),
    path("send_email/",send_email_assistant,name="邮件发送助手"),
]
