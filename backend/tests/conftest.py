"""
Pytest 配置和共享 fixtures
"""

import pytest
import sys
import os

# 将项目根目录添加到路径
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_path)


@pytest.fixture(scope="session")
def project_root():
    """项目根目录"""
    return os.path.dirname(backend_path)


@pytest.fixture(scope="session")
def test_data_dir(project_root):
    """测试数据目录"""
    return os.path.join(project_root, "test_data")


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """自动设置测试环境变量"""
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
