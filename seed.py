"""Seed dữ liệu mẫu cho TOÀN HỆ THỐNG. Chạy được trên database mới tinh (chưa có bảng nào).

    cd backend
    python seed.py                 # tạo bảng còn thiếu + thêm dữ liệu mẫu còn thiếu
    python seed.py --reset --yes   # XOÁ SẠCH mọi bảng rồi seed lại từ đầu (mất hết dữ liệu hiện có!)

- Chạy lại nhiều lần không bị trùng: mỗi bản ghi được tìm theo khoá tự nhiên (email, tên, mã...) trước khi tạo.
- Không ghi đè dữ liệu đang có (không đổi mật khẩu tài khoản cũ).
- Cũng chạy tốt trên DB đã chạy sql/init.sql: các bản ghi trùng tên / email sẽ được bỏ qua.
- Mật khẩu của mọi tài khoản mẫu: Restaurant@123
"""
import argparse
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models  # noqa: F401 - import để SQLAlchemy biết các bảng
from app.core.security import hash_password
from app.db import session as dbs
from app.models.branch import Branch
from app.models.branch_inventory import BranchInventory
from app.models.category import Category
from app.models.customer import Customer
from app.models.dining_table import DiningTable
from app.models.ingredient import Ingredient
from app.models.menu_item import MenuItem
from app.models.menu_item_option import MenuItemOption
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.order_item_option import OrderItemOption
from app.models.payment import Payment
from app.models.recipe import Recipe
from app.models.reservation import Reservation
from app.models.role import Role
from app.models.user import User
from app.models.voucher import Voucher

DEFAULT_PASSWORD = "Restaurant@123"
SEED_NOTE = "[seed]"  # đánh dấu order mẫu để chạy lại không tạo thêm

ROLES = ["admin", "manager", "cashier", "waiter", "kitchen"]

BRANCHES = [  # (tên, địa chỉ, sđt)
    ("Chi nhánh Quận 1", "8/15 Lê Thánh Tôn, Quận 1, TP.HCM", "02812345678"),
    ("Chi nhánh Hà Nội", "43 Phan Kế Bình, Ba Đình, Hà Nội", "02487654321"),
    ("Chi nhánh Đà Nẵng", "25 Bạch Đằng, Hải Châu, Đà Nẵng", "02363123456"),
]

USERS = [  # (email, họ tên, vai trò, chi nhánh theo tên hoặc None, sđt)
    ("admin@restaurant.com", "Quản trị viên", "admin", None, None),
    ("manager@restaurant.com", "Nguyễn Văn A", "manager", BRANCHES[0][0], "0901000001"),
    ("cashier@restaurant.com", "Trần Thị B", "cashier", BRANCHES[0][0], "0901000002"),
    ("waiter@restaurant.com", "Lê Văn C", "waiter", BRANCHES[0][0], "0901000003"),
    ("kitchen@restaurant.com", "Phạm Thị D", "kitchen", BRANCHES[0][0], "0901000004"),
    ("waiter2@restaurant.com", "Hoàng Văn E", "waiter", BRANCHES[0][0], "0901000005"),
    ("manager.hn@restaurant.com", "Vũ Thị F", "manager", BRANCHES[1][0], "0902000001"),
    ("cashier.hn@restaurant.com", "Đặng Văn G", "cashier", BRANCHES[1][0], "0902000002"),
    ("waiter.hn@restaurant.com", "Bùi Thị H", "waiter", BRANCHES[1][0], "0902000003"),
    ("kitchen.hn@restaurant.com", "Ngô Văn I", "kitchen", BRANCHES[1][0], "0902000004"),
    ("manager.dn@restaurant.com", "Đỗ Thị K", "manager", BRANCHES[2][0], "0903000001"),
    ("waiter.dn@restaurant.com", "Lý Văn L", "waiter", BRANCHES[2][0], "0903000002"),
    ("locked@restaurant.com", "Nhân viên đã nghỉ việc", "waiter", BRANCHES[0][0], "0901999999"),  # tài khoản bị khoá
]
LOCKED_EMAILS = {"locked@restaurant.com"}

CATEGORIES = ["Khai vị", "Pizza", "Pasta", "Salad", "Đồ uống", "Tráng miệng"]

MENU = [  # (danh mục, tên, mô tả, giá, còn món?)
    ("Pizza", "Pizza Margherita", "Pizza phủ mozzarella và cà chua", 150000, True),
    ("Pizza", "Pizza Hải Sản", "Pizza hải sản tươi", 190000, True),
    ("Pizza", "Pizza Pepperoni", "Xúc xích cay kiểu Ý", 170000, True),
    ("Pizza", "Pizza Phô Mai 4 Loại", "Mozzarella, gorgonzola, parmesan, fontina", 180000, True),
    ("Pizza", "Pizza Hawaii", "Dứa và giăm bông", 160000, True),
    ("Pasta", "Mì Ý Cua", "Mì Ý sốt cua béo", 180000, True),
    ("Pasta", "Mì Ý Carbonara", "Sốt kem trứng và thịt xông khói", 160000, True),
    ("Pasta", "Mì Ý Bò Bằm", "Mì Ý sốt cà chua bò bằm", 165000, True),
    ("Pasta", "Mì Ý Hải Sản Sốt Cà", "Tôm, mực, nghêu sốt cà chua", 185000, True),
    ("Pasta", "Lasagna Bò Nướng Phô Mai", "Lasagna bò bằm nướng phô mai", 170000, True),
    ("Khai vị", "Bánh Mì Bơ Tỏi", "Bánh mì nướng bơ tỏi giòn", 45000, True),
    ("Khai vị", "Súp Kem Nấm", "Súp kem nấm nóng", 55000, True),
    ("Khai vị", "Khoai Tây Chiên", "Khoai tây chiên giòn", 50000, True),
    ("Salad", "Salad Rau Củ", "Rau củ tươi trong ngày", 90000, True),
    ("Salad", "Salad Caesar", "Gà nướng, phô mai parmesan", 110000, True),
    ("Đồ uống", "Chanh Tươi", "Chanh tươi mát lạnh", 40000, True),
    ("Đồ uống", "Cà Phê Sữa Đá", "Cà phê phin sữa đá", 35000, True),
    ("Đồ uống", "Nước Suối", "Chai 500ml", 20000, True),
    ("Đồ uống", "Nước ép cam", "Cam vắt tươi", 50000, True),
    ("Đồ uống", "Trà đào", "Trà đào cam sả", 45000, True),
    ("Đồ uống", "Coca-Cola", "Lon 330ml", 30000, True),
    ("Tráng miệng", "Kem Gelato", "Kem kiểu Ý, 2 viên", 55000, True),
    ("Tráng miệng", "Bánh Phô Mai", "Cheesecake kiểu New York", 75000, True),
    ("Tráng miệng", "Tiramisu", "Bánh tiramisu cacao", 70000, True),
    ("Tráng miệng", "Panna Cotta", "Món đang hết hàng", 65000, False),
]

MENU_IMAGES = {
    "Pizza Margherita": "assets/images/menu/pizza-margherita.jpg",
    "Pizza Hải Sản": "assets/images/menu/pizza-hai-san.jpg",
    "Pizza Pepperoni": "assets/images/menu/pizza-pepperoni.jpg",
    "Pizza Phô Mai 4 Loại": "assets/images/menu/pizza-pho-mai-4-loai.jpg",
    "Pizza Hawaii": "assets/images/menu/pizza-hawaii.jpg",
    "Mì Ý Bò Bằm": "assets/images/menu/mi-y-bo-bam.jpg",
    "Mì Ý Carbonara": "assets/images/menu/mi-y-carbonara.jpg",
    "Mì Ý Hải Sản Sốt Cà": "assets/images/menu/mi-y-hai-san-sot-ca.jpg",
    "Lasagna Bò Nướng Phô Mai": "assets/images/menu/lasagna-bo-nuong-pho-mai.jpg",
    "Salad Rau Củ": "assets/images/menu/salad-rau-cu.jpg",
    "Salad Caesar": "assets/images/menu/salad-caesar.jpg",
    "Bánh Mì Bơ Tỏi": "assets/images/menu/banh-mi-bo-toi.jpg",
    "Súp Kem Nấm": "assets/images/menu/sup-kem-nam.jpg",
    "Khoai Tây Chiên": "assets/images/menu/khoai-tay-chien.jpg",
    "Nước ép cam": "assets/images/menu/nuoc-ep-cam.jpg",
    "Trà đào": "assets/images/menu/tra-dao.jpg",
    "Coca-Cola": "assets/images/menu/coca-cola.jpg",
    "Chanh Tươi": "assets/images/menu/chanh-tuoi.jpg",
    "Cà Phê Sữa Đá": "assets/images/menu/ca-phe-sua-da.jpg",
    "Nước Suối": "assets/images/menu/nuoc-suoi.jpg",
    "Tiramisu": "assets/images/menu/tiramisu.jpg",
    "Panna Cotta": "assets/images/menu/panna-cotta.jpg",
    "Kem Gelato": "assets/images/menu/kem-gelato.jpg",
    "Bánh Phô Mai": "assets/images/menu/banh-pho-mai.jpg",
    "Mì Ý Cua": "assets/images/menu/mi-y-cua.jpg",
}

OPTIONS = [  # (tên món, tên tuỳ chọn, size, topping, giá thêm)
    ("Pizza Margherita", "Size M", "M", None, 20000),
    ("Pizza Margherita", "Size L", "L", None, 40000),
    ("Pizza Margherita", "Thêm phô mai", None, "Phô mai", 20000),
    ("Pizza Hải Sản", "Size L", "L", None, 40000),
    ("Pizza Hải Sản", "Thêm phô mai", None, "Phô mai", 20000),
    ("Pizza Pepperoni", "Size L", "L", None, 40000),
    ("Trà đào", "Thêm trân châu", None, "Trân châu", 10000),
]

TABLES = {  # tên chi nhánh -> [(số bàn, số ghế, khu vực)]
    BRANCHES[0][0]: [("A1", 2, "Tầng 1"), ("A2", 4, "Tầng 1"), ("A3", 4, "Tầng 1"), ("A4", 6, "Tầng 2"), ("A5", 8, "Tầng 2")],
    BRANCHES[1][0]: [("B1", 2, "Tầng 1"), ("B2", 4, "Tầng 1"), ("B3", 6, "Sân vườn")],
    BRANCHES[2][0]: [("C1", 2, "Tầng 1"), ("C2", 4, "Tầng 1"), ("C3", 6, "Tầng 2")],
}

CUSTOMERS = [("Nguyễn Khách Một", "0911000001"), ("Trần Khách Hai", "0911000002"), ("Lê Khách Ba", "0911000003")]

INGREDIENTS = [("Bột mì", "g"), ("Phô mai mozzarella", "g"), ("Cà chua", "g"), ("Cua", "g"), ("Mì Ý", "g"), ("Thịt xông khói", "g"), ("Cam tươi", "g"), ("Thịt bò bằm", "g"), ("Khoai tây", "g"),]
RECIPES = [  # (tên món, nguyên liệu, lượng cho 1 phần)
    ("Pizza Margherita", "Bột mì", 200), ("Pizza Margherita", "Phô mai mozzarella", 100), ("Pizza Margherita", "Cà chua", 80),
    ("Pizza Hải Sản", "Bột mì", 200), ("Pizza Hải Sản", "Phô mai mozzarella", 100),
    ("Mì Ý Cua", "Mì Ý", 150), ("Mì Ý Cua", "Cua", 80),
    ("Mì Ý Carbonara", "Mì Ý", 150), ("Mì Ý Carbonara", "Thịt xông khói", 60),
    ("Nước ép cam", "Cam tươi", 300),
    ("Mì Ý Bò Bằm", "Mì Ý", 150), ("Mì Ý Bò Bằm", "Thịt bò bằm", 100), ("Mì Ý Bò Bằm", "Cà chua", 80),
    ("Khoai Tây Chiên", "Khoai tây", 200),
    ("Pizza Hawaii", "Bột mì", 200), ("Pizza Hawaii", "Phô mai mozzarella", 100),
]
INVENTORY = {"Bột mì": (5000, 1000), "Phô mai mozzarella": (3000, 500), "Cà chua": (2000, 400), "Cua": (1500, 300),
             "Mì Ý": (4000, 800), "Thịt xông khói": (1200, 300), "Cam tươi": (350, 400), "Thịt bò bằm": (2000, 400), "Khoai tây": (3000, 500),}  # Cam tươi: dưới mức tối thiểu (để thử cảnh báo)

VOUCHERS = [  # (mã, loại, giá trị, đơn tối thiểu, bắt đầu, kết thúc, số lượt, đang hoạt động)
    ("WELCOME10", "percent", 10, 200000, -30, 60, 100, True),
    ("GIAM50K", "amount", 50000, 300000, -30, 60, None, True),
    ("HETHAN", "percent", 20, 0, -90, -1, 50, True),  # đã hết hạn, để thử báo lỗi
    ("NGUNG", "amount", 10000, 0, -30, 60, None, False),  # đã ngừng, để thử báo lỗi
]


class Stats:
    def __init__(self):
        self.created, self.skipped = {}, {}

    def add(self, name, created):
        bucket = self.created if created else self.skipped
        bucket[name] = bucket.get(name, 0) + 1


def get_or_create(db: Session, stats: Stats, model, lookup: dict, defaults: dict | None = None):
    """Tìm theo `lookup`; chưa có thì tạo mới với lookup + defaults. Trả về bản ghi."""
    obj = db.scalar(select(model).filter_by(**lookup))
    if obj is not None:
        stats.add(model.__tablename__, False)
        return obj
    obj = model(**lookup, **(defaults or {}))
    db.add(obj)
    db.flush()  # lấy id ngay để bản ghi sau tham chiếu
    stats.add(model.__tablename__, True)
    return obj


def seed(db: Session) -> Stats:
    stats = Stats()
    today = date.today()

    roles = {name: get_or_create(db, stats, Role, {"name": name}) for name in ROLES}
    branches = {
        name: get_or_create(db, stats, Branch, {"name": name}, {"address": address, "phone": phone})
        for name, address, phone in BRANCHES
    }

    password_hash = None  # tính 1 lần khi thật sự cần (bcrypt hơi chậm)
    users = {}
    for email, full_name, role, branch_name, phone in USERS:
        user = db.scalar(select(User).where(func.lower(User.email) == email))
        is_new = user is None
        if is_new:
            password_hash = password_hash or hash_password(DEFAULT_PASSWORD)
            user = User(
                email=email, full_name=full_name, phone=phone, password_hash=password_hash,
                role_id=roles[role].id, branch_id=branches[branch_name].id if branch_name else None,
                is_active=email not in LOCKED_EMAILS,
            )
            db.add(user)
            db.flush()
        stats.add("users", is_new)
        users[email] = user

    categories = {
        name: get_or_create(db, stats, Category, {"name": name}, {"sort_order": i + 1})
        for i, name in enumerate(CATEGORIES)
    }
    items = {}
    for category, name, description, price, available in MENU:
        items[name] = get_or_create(
            db, stats, MenuItem, {"name": name},
            {"category_id": categories[category].id, "description": description, "price": Decimal(price),
             "is_available": available, "image_url": MENU_IMAGES.get(name)},
        )
        # DB đã có món từ trước mà chưa có ảnh thì bổ sung; món đã có ảnh (sửa tay) thì giữ nguyên
        if items[name].image_url is None and name in MENU_IMAGES:
            items[name].image_url = MENU_IMAGES[name]
    options = {}
    for item_name, name, size, topping, extra in OPTIONS:
        options[(item_name, name)] = get_or_create(
            db, stats, MenuItemOption, {"menu_item_id": items[item_name].id, "name": name},
            {"size": size, "topping": topping, "extra_price": Decimal(extra)},
        )

    tables = {}
    for branch_name, rows in TABLES.items():
        for number, capacity, area in rows:
            tables[(branch_name, number)] = get_or_create(
                db, stats, DiningTable, {"branch_id": branches[branch_name].id, "table_number": number},
                {"capacity": capacity, "area": area},
            )

    customers = [
        get_or_create(db, stats, Customer, {"phone": phone}, {"full_name": full_name}) for full_name, phone in CUSTOMERS
    ]

    ingredients = {name: get_or_create(db, stats, Ingredient, {"name": name}, {"unit": unit}) for name, unit in INGREDIENTS}
    for item_name, ingredient_name, qty in RECIPES:
        get_or_create(
            db, stats, Recipe, {"menu_item_id": items[item_name].id, "ingredient_id": ingredients[ingredient_name].id},
            {"quantity_needed": Decimal(qty)},
        )
    for branch in branches.values():
        for ingredient_name, (qty, minimum) in INVENTORY.items():
            get_or_create(
                db, stats, BranchInventory, {"branch_id": branch.id, "ingredient_id": ingredients[ingredient_name].id},
                {"quantity": Decimal(qty), "min_quantity": Decimal(minimum)},
            )

    vouchers = {}
    for code, kind, value, minimum, start, end, limit, active in VOUCHERS:
        vouchers[code] = get_or_create(
            db, stats, Voucher, {"code": code},
            {"discount_type": kind, "discount_value": Decimal(value), "min_order_amount": Decimal(minimum),
             "start_date": today + timedelta(days=start), "end_date": today + timedelta(days=end),
             "usage_limit": limit, "is_active": active},
        )

    # ---- Đặt bàn mẫu (chi nhánh Quận 1) ----
    q1 = branches[BRANCHES[0][0]]

    def at(days: int, hour: int) -> datetime:
        return datetime.combine(today + timedelta(days=days), datetime.min.time()).replace(hour=hour)

    for code, customer, table, party, when, status in [
        ("DBSEED01", customers[0], "A2", 3, at(1, 19), "pending"),
        ("DBSEED02", customers[1], "A4", 5, at(2, 18), "confirmed"),
        ("DBSEED03", customers[2], "A1", 2, at(3, 12), "cancelled"),
    ]:
        get_or_create(
            db, stats, Reservation, {"code": code},
            {"branch_id": q1.id, "table_id": tables[(q1.name, table)].id, "customer_id": customer.id,
             "guest_name": customer.full_name, "guest_phone": customer.phone, "party_size": party,
             "reserved_at": when, "status": status},
        )

    # ---- Order mẫu (chi nhánh Quận 1): 1 đã thanh toán + 1 đang phục vụ ----
    waiter, cashier = users["waiter@restaurant.com"], users["cashier@restaurant.com"]
    if db.scalar(select(Order.id).where(Order.note == SEED_NOTE).limit(1)) is None:
        def add_order(table_number, status, lines):
            order = Order(branch_id=q1.id, table_id=tables[(q1.name, table_number)].id, waiter_id=waiter.id,
                          status=status, note=SEED_NOTE)
            db.add(order)
            for item_name, qty, option_names, item_status in lines:
                item = items[item_name]
                order_item = OrderItem(menu_item_id=item.id, quantity=qty, unit_price=item.price, status=item_status,
                                       sent_at=datetime.now() if item_status != "pending" else None)
                for option_name in option_names:
                    option = options[(item_name, option_name)]
                    order_item.options.append(OrderItemOption(option_id=option.id, extra_price=option.extra_price))
                order.items.append(order_item)
            db.flush()
            return order

        paid = add_order("A2", "paid", [("Pizza Margherita", 2, ["Size L"], "served"), ("Salad Rau Củ", 1, [], "served")])
        paid.closed_at = datetime.now()
        subtotal = paid.subtotal
        db.add(Payment(order_id=paid.id, cashier_id=cashier.id, voucher_id=None, subtotal=subtotal,
                       discount_amount=Decimal(0), total_amount=subtotal, method="cash", status="paid"))
        add_order("A3", "sent", [("Mì Ý Cua", 1, [], "cooking"), ("Nước ép cam", 2, [], "pending")])
        tables[(q1.name, "A3")].status = "occupied"
        stats.add("orders", True)
    else:
        stats.add("orders", False)

    seed_extra(db, stats, {"roles": roles, "branches": branches, "users": users, "tables": tables, "items": items,
                           "options": options, "vouchers": vouchers, "customers": customers})
    db.commit()
    return stats

SEED2_NOTE = "[seed2]"  # đánh dấu order mẫu bổ sung, chạy lại không tạo thêm
CAN_THO = ("Chi nhánh Cần Thơ", "12 Hòa Bình, Ninh Kiều, Cần Thơ", "02923111222")  # chi nhánh ngừng hoạt động

EXTRA_USERS = [  # (email, họ tên, vai trò, chi nhánh, sđt)
    ("cashier2@restaurant.com", "Tạ Thị M", "cashier", BRANCHES[0][0], "0901000006"),
    ("waiter3@restaurant.com", "Châu Văn N", "waiter", BRANCHES[0][0], "0901000007"),
    ("kitchen2@restaurant.com", "Mai Thị O", "kitchen", BRANCHES[0][0], "0901000008"),
    ("cashier.dn@restaurant.com", "Trương Văn P", "cashier", BRANCHES[2][0], "0903000003"),
    ("kitchen.dn@restaurant.com", "Phan Thị Q", "kitchen", BRANCHES[2][0], "0903000004"),
    ("manager.ct@restaurant.com", "Võ Văn R", "manager", CAN_THO[0], "0904000001"),  # quản lý chi nhánh đã đóng
]
EXTRA_CUSTOMERS = [
    ("Phạm Thị Hoa", "0911000004"), ("Đỗ Minh Quân", "0911000005"), ("Vũ Ngọc Lan", "0911000006"),
    ("Bùi Anh Tuấn", "0911000007"), ("Hoàng Mai Chi", "0911000008"),
]
EXTRA_VOUCHERS = [  # (mã, loại, giá trị, đơn tối thiểu, bắt đầu, kết thúc, số lượt, đang hoạt động)
    ("DOIDIEM20", "amount", 20000, 0, -10, 20, 1, True),   # voucher "đổi từ điểm"
    ("SAPHET", "percent", 15, 100000, -30, 60, 3, True),   # sắp hết lượt (đã dùng 2/3)
]
# (số ngày trước, giờ, chi nhánh, bàn, món [(tên, SL, [tuỳ chọn])], phương thức, mã voucher, SĐT tích điểm)
EXTRA_PAID = [
    (6, 12, 0, "A2", [("Pizza Margherita", 2, ["Size L"]), ("Nước ép cam", 2, [])], "cash", None, None),
    (6, 19, 0, "A4", [("Pizza Hải Sản", 2, []), ("Mì Ý Cua", 2, []), ("Tiramisu", 3, [])], "card", "WELCOME10", "0911000004"),
    (5, 13, 1, "B2", [("Mì Ý Carbonara", 2, []), ("Trà đào", 2, ["Thêm trân châu"])], "transfer", None, "0911000005"),
    (4, 20, 0, "A5", [("Pizza Pepperoni", 3, ["Size L"]), ("Salad Caesar", 2, []), ("Coca-Cola", 4, [])], "cash", "GIAM50K", "0911000004"),
    (3, 12, 2, "C2", [("Lasagna Bò Nướng Phô Mai", 2, []), ("Chanh Tươi", 2, [])], "cash", None, None),
    (3, 18, 1, "B3", [("Pizza Phô Mai 4 Loại", 2, []), ("Súp Kem Nấm", 2, []), ("Kem Gelato", 2, [])], "card", None, "0911000006"),
    (2, 19, 0, "A3", [("Pizza Hawaii", 1, []), ("Mì Ý Bò Bằm", 1, []), ("Cà Phê Sữa Đá", 2, [])], "transfer", None, "0911000007"),
    (2, 21, 2, "C3", [("Pizza Hải Sản", 3, ["Size L"]), ("Salad Rau Củ", 2, [])], "card", "SAPHET", "0911000008"),
    (1, 12, 0, "A2", [("Mì Ý Cua", 2, []), ("Bánh Mì Bơ Tỏi", 1, [])], "cash", None, "0911000005"),
    (1, 19, 1, "B1", [("Pizza Margherita", 1, ["Size M"]), ("Khoai Tây Chiên", 1, [])], "cash", None, None),
    (1, 20, 0, "A4", [("Pizza Pepperoni", 2, []), ("Pizza Hải Sản", 2, []), ("Bánh Phô Mai", 4, []), ("Nước Suối", 4, [])], "card", "WELCOME10", "0911000004"),
    (0, 11, 0, "A1", [("Salad Caesar", 1, []), ("Trà đào", 1, [])], "cash", None, None),
]
# order đang phục vụ: (chi nhánh, bàn, trạng thái order, món [(tên, SL, trạng thái món)])
EXTRA_OPEN = [
    (0, "A4", "open", [("Pizza Margherita", 2, "pending")]),
    (0, "A5", "served", [("Pizza Pepperoni", 2, "served"), ("Coca-Cola", 3, "served")]),
    (1, "B2", "sent", [("Mì Ý Carbonara", 2, "cooking"), ("Nước Suối", 2, "done")]),
    (2, "C2", "sent", [("Lasagna Bò Nướng Phô Mai", 1, "cooking")]),
]


def seed_extra(db: Session, stats: Stats, ctx: dict) -> None:
    """Thêm dữ liệu mẫu bổ sung: nhân viên/chi nhánh, khách + điểm, đặt bàn, order + thanh toán nhiều ngày."""
    from app.crud.loyalty import points_for
    from app.models.loyalty import LoyaltyTransaction

    today, now = date.today(), datetime.now()
    roles, branches, users, tables, items, options, vouchers = (
        ctx[k] for k in ("roles", "branches", "users", "tables", "items", "options", "vouchers"))
    branch_list = [branches[b[0]] for b in BRANCHES]

    # ---- 1. Nhân viên & chi nhánh ----
    can_tho = get_or_create(db, stats, Branch, {"name": CAN_THO[0]}, {"address": CAN_THO[1], "phone": CAN_THO[2], "is_active": False})
    branches[CAN_THO[0]] = can_tho
    password_hash = None
    for email, full_name, role, branch_name, phone in EXTRA_USERS:
        user = db.scalar(select(User).where(func.lower(User.email) == email))
        is_new = user is None
        if is_new:
            password_hash = password_hash or hash_password(DEFAULT_PASSWORD)
            user = User(email=email, full_name=full_name, phone=phone, password_hash=password_hash,
                        role_id=roles[role].id, branch_id=branches[branch_name].id, is_active=True)
            db.add(user)
            db.flush()
        stats.add("users", is_new)
        users[email] = user

    # ---- 2. Khách hàng + voucher bổ sung ----
    customers = {phone: get_or_create(db, stats, Customer, {"phone": phone}, {"full_name": name}) for name, phone in EXTRA_CUSTOMERS}
    for c in ctx["customers"]:
        customers[c.phone] = c
    for code, kind, value, minimum, start, end, limit, active in EXTRA_VOUCHERS:
        vouchers[code] = get_or_create(
            db, stats, Voucher, {"code": code},
            {"discount_type": kind, "discount_value": Decimal(value), "min_order_amount": Decimal(minimum),
             "start_date": today + timedelta(days=start), "end_date": today + timedelta(days=end),
             "usage_limit": limit, "is_active": active})

    # ---- 3. Đặt bàn đủ trạng thái, nhiều chi nhánh ----
    def at(days, hour, minute=0):
        return datetime.combine(today + timedelta(days=days), datetime.min.time()).replace(hour=hour, minute=minute)

    phones = list(customers)
    for i, (code, b, table, party, when, status, note) in enumerate([
        ("DBSEED04", 0, "A2", 4, at(0, 18, 30), "confirmed", "Sinh nhật, cần bánh kem"),
        ("DBSEED05", 0, "A3", 2, at(0, 19), "pending", None),
        ("DBSEED06", 0, "A5", 8, at(0, 20), "confirmed", "Họp lớp"),
        ("DBSEED07", 0, "A1", 2, now.replace(minute=0, second=0, microsecond=0), "seated", "Khách đã nhận bàn"),
        ("DBSEED08", 0, "A2", 3, at(-1, 12), "pending", "Quá giờ, chưa tới (để thử no-show)"),
        ("DBSEED09", 0, "A3", 2, at(-2, 19), "no_show", None),
        ("DBSEED10", 0, "A4", 5, at(-3, 18), "seated", None),
        ("DBSEED11", 0, "A1", 2, at(4, 12), "cancelled", "Khách huỷ vì bận"),
        ("DBSEED12", 1, "B2", 4, at(0, 19), "confirmed", None),
        ("DBSEED13", 1, "B3", 6, at(1, 18), "pending", None),
        ("DBSEED14", 2, "C2", 4, at(1, 12), "confirmed", None),
        ("DBSEED15", 2, "C3", 6, at(2, 19), "pending", "Gần cửa sổ"),
    ]):
        cust = customers[phones[i % len(phones)]]
        branch = branch_list[b]
        get_or_create(
            db, stats, Reservation, {"code": code},
            {"branch_id": branch.id, "table_id": tables[(branch.name, table)].id, "customer_id": cust.id,
             "guest_name": cust.full_name, "guest_phone": cust.phone, "party_size": party,
             "reserved_at": when, "status": status, "note": note})

    # ---- 4. Order + thanh toán nhiều ngày, order đang phục vụ ----
    if db.scalar(select(Order.id).where(Order.note == SEED2_NOTE).limit(1)) is not None:
        stats.add("orders", False)
        return

    staff = {0: ("waiter@restaurant.com", "cashier@restaurant.com"),
             1: ("waiter.hn@restaurant.com", "cashier.hn@restaurant.com"),
             2: ("waiter.dn@restaurant.com", "cashier.dn@restaurant.com")}

    def build(b, table, status, lines, created):
        branch = branch_list[b]
        order = Order(branch_id=branch.id, table_id=tables[(branch.name, table)].id,
                      waiter_id=users[staff[b][0]].id, status=status, note=SEED2_NOTE, created_at=created)
        db.add(order)
        for name, qty, opts, *rest in lines:
            item = items[name]
            line = OrderItem(menu_item_id=item.id, quantity=qty, unit_price=item.price,
                             status=rest[0] if rest else "served", sent_at=created if (rest[0] if rest else "served") != "pending" else None)
            for opt in opts if isinstance(opts, list) else []:
                o = options[(name, opt)]
                line.options.append(OrderItemOption(option_id=o.id, extra_price=o.extra_price))
            order.items.append(line)
        db.flush()
        return order

    payments = {}
    for days, hour, b, table, lines, method, code, phone in EXTRA_PAID:
        created = at(-days, hour) if days else now.replace(hour=min(hour, now.hour), minute=0, second=0, microsecond=0)
        order = build(b, table, "paid", [(n, q, o) for n, q, o in lines], created)
        order.closed_at = created + timedelta(minutes=75)
        subtotal, discount, voucher = order.subtotal, Decimal(0), vouchers.get(code) if code else None
        if voucher is not None:
            if subtotal >= voucher.min_order_amount:
                discount = (subtotal * voucher.discount_value / 100).quantize(Decimal(1)) if voucher.discount_type == "percent" else voucher.discount_value
            voucher.used_count += 1
        pay = Payment(order_id=order.id, cashier_id=users[staff[b][1]].id, voucher_id=voucher.id if voucher else None,
                      subtotal=subtotal, discount_amount=discount, total_amount=subtotal - discount,
                      method=method, status="paid", paid_at=order.closed_at)
        db.add(pay)
        db.flush()
        payments[(days, hour, b, table)] = (pay, phone)
    vouchers["SAPHET"].used_count = max(vouchers["SAPHET"].used_count, 2)

    # điểm tích luỹ: earn theo từng payment có SĐT; redeem 1 lần để thử lịch sử
    for pay, phone in payments.values():
        points = points_for(pay.total_amount)
        if phone and points > 0:
            db.add(LoyaltyTransaction(customer_id=customers[phone].id, payment_id=pay.id, type="earn",
                                      points=points, created_at=pay.paid_at))
    db.add(LoyaltyTransaction(customer_id=customers["0911000004"].id, voucher_id=vouchers["DOIDIEM20"].id,
                              type="redeem", points=-20, created_at=now - timedelta(days=1)))
    vouchers["DOIDIEM20"].used_count = 0  # voucher chưa dùng, khách còn có thể thử áp vào đơn

    for b, table, status, lines in EXTRA_OPEN:
        build(b, table, status, lines, now - timedelta(minutes=40))
        tables[(branch_list[b].name, table)].status = "occupied"
    stats.add("orders", True)

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Seed dữ liệu mẫu toàn hệ thống")
    parser.add_argument("--reset", action="store_true", help="XOÁ SẠCH mọi bảng rồi tạo lại (mất hết dữ liệu!)")
    parser.add_argument("--yes", action="store_true", help="Không hỏi lại khi dùng --reset")
    args = parser.parse_args(argv)

    engine = dbs.engine
    if args.reset:
        if not args.yes and input(f"XOÁ SẠCH database '{engine.url.database}'? Gõ 'yes' để tiếp tục: ").strip() != "yes":
            print("Đã huỷ.")
            return 1
        dbs.Base.metadata.drop_all(bind=engine)
        print("Đã xoá toàn bộ bảng.")
    dbs.Base.metadata.create_all(bind=engine)  # tạo bảng còn thiếu (DB sạch thì tạo hết)

    with Session(engine) as db:
        stats = seed(db)

    print("\nSeed xong. (mới tạo / đã có sẵn)")
    for table in sorted(set(stats.created) | set(stats.skipped)):
        print(f"  {table:20} {stats.created.get(table, 0):3} / {stats.skipped.get(table, 0)}")
    print(f"\nTài khoản mẫu (mật khẩu chung: {DEFAULT_PASSWORD}):")
    for email, full_name, role, branch_name, _ in USERS:
        note = "  [bị khoá]" if email in LOCKED_EMAILS else ""
        print(f"  {role:8} {email:30} {branch_name or '(tất cả chi nhánh)'}{note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())