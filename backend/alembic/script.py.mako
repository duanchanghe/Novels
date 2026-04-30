# ===========================================
# Alembic 脚本模板
# ===========================================

"""
Alembic 迁移脚本模板配置

定义自动生成迁移脚本的模板。
"""

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if prompt else ""}


def downgrade() -> None:
    ${downgrades if prompt else ""}
