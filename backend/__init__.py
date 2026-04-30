# ===========================================
# AI 有声书工坊 - 后端主模块
# ===========================================

"""
AI 有声书工坊后端应用

提供 EPUB 电子书到 AI 有声书的自动化转换服务。

模块结构：
- api: API 路由层
- core: 核心配置与中间件
- models: SQLAlchemy 数据模型
- services: 业务逻辑服务
- tasks: Celery 异步任务
- schemas: Pydantic 数据模型
- utils: 工具函数
"""

__version__ = "0.1.0"
__author__ = "AI Audiobook Workshop Team"
