# RAG
用于人工智能课程的RAG项目

## 课程笔记

### 2026.10.13
#### 课程主要内容:
本次启动会明确了两周项目实践安排。课程以小组为单位，基于 RAG 技术用 Python 开发校园助手、旅游助手类智能体雏形。
#### 代码及实践:
同时仅就今天而言,主要学习了使用miniforge创建并管理一个python=3.12的虚拟环境,学习了几条基础的conda命令:
- conda –version  输出conda的版本,常用于校验系统conda是否可用
- conda create –n RAG.env python=3.12  创建名为”RAG.env”,且python版本为3.12的虚拟环境,用于隔离不同项目的依赖,防止版本冲突
- conda activate RAG.env  激活”RAG.env”环境
- conda deactivate  关闭当前环境
- conda env list  查看conda管理的虚拟环境(包括名称及其路径)
- 并简单介绍了”客户端—服务端”模型,同时安装了Django服务器框架

### 2026.10.16-17
#### 课程主要内容:
##### Django项目目录结构梳理:
- asgi.py和wsgi.py：上线时使用的网络代理文件，开发阶段无需关注。
- urls.py：核心路由配置文件，负责前端访问路径映射。
- settings.py：项目全局配置文件。
- manage.py：Django管理脚本，用于执行启动服务器等命令（如runserver）。
##### 代码实践:
- 用 ChatOpenAI 实例化模型，配置 model、api_key、base_url、temperature；
- 用单例加线程锁把调用封装成 llm.py；
- 用 pydantic 定义邮件参数，smtplib 连 QQ 邮箱 SSL 发信，以 @tool 注册为工具，再在 views.py 接入记忆组件。


