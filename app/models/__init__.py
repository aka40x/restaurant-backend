# Import mọi model ở đây để Base.metadata.create_all() "nhìn thấy" và tạo bảng.
# Thêm model mới -> nhớ thêm 1 dòng import vào file này (mỗi người chỉ thêm dòng của module mình).
from app.models.branch import Branch  # noqa: F401
from app.models.role import Role  # noqa: F401
from app.models.user import User  # noqa: F401