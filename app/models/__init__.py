# Import mọi model ở đây để Base.metadata.create_all() "nhìn thấy" và tạo bảng.
# Thêm model mới -> nhớ thêm 1 dòng import vào file này (mỗi người chỉ thêm dòng của module mình).
from app.models.branch import Branch  # noqa: F401
from app.models.role import Role  # noqa: F401
from app.models.user import User  # noqa: F401

from app.models.voucher import Voucher  # noqa: F401
from app.models.payment import Payment  # noqa: F401
from app.models.ingredient import Ingredient  # noqa: F401
from app.models.recipe import Recipe  # noqa: F401
from app.models.branch_inventory import BranchInventory  # noqa: F401
from app.models.category import Category  # noqa: F401
from app.models.menu_item import MenuItem  # noqa: F401
from app.models.menu_item_option import MenuItemOption  # noqa: F401
from app.models.dining_table import DiningTable  # noqa: F401
from app.models.order import Order  # noqa: F401
from app.models.order_item import OrderItem  # noqa: F401
from app.models.order_item_option import OrderItemOption  # noqa: F401
from app.models.revoked_token import RevokedToken  # noqa: F401
from app.models.customer import Customer
from app.models.reservation import Reservation