from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import get_db
from models.order import Order, OrderItem, OrderItemOption
# Nếu project của bạn có model Menu Item / Table, hãy import tương ứng
# from models.menu import MenuItem
# from models.table import DiningTable
from schemas.order import OrderCreate, OrderItemCreate, OrderResponse
from responses import success_response, error_response

router = APIRouter(prefix="/api/orders", tags=["Orders"])

@router.post("", summary="Mở order mới cho bàn")
def create_order(payload: OrderCreate, request: Request, db: Session = Depends(get_db)):
    # 1. Kiểm tra xem bàn đã có order đang mở (status='open') hay chưa (tuỳ chọn nghiệp vụ)
    existing_order = db.query(Order).filter(
        Order.table_id == payload.table_id, 
        Order.status == "open"
    ).first()
    
    if existing_order:
        # Nếu bàn đã mở order rồi, có thể gộp thêm hoặc báo lỗi nhẹ tuỳ nhóm. 
        # Ở đây ta cho phép dùng chung order đang mở hoặc tạo mới nếu cần.
        pass

    # 2. Tạo Order mới
    new_order = Order(
        branch_id=payload.branch_id,
        table_id=payload.table_id,
        reservation_id=payload.reservation_id,
        waiter_id=1,  # Có thể lấy từ token đăng nhập của nhân viên (current_user.id)
        status="open",
        note=payload.note
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # 3. Xử lý thêm các món ăn ban đầu (nếu có gửi kèm trong payload)
    total_amount = 0
    for item_data in payload.items:
        # TODO: Kiểm tra món ăn có tồn tại và còn hàng không (is_available / stock)
        # menu_item = db.query(MenuItem).filter(MenuItem.id == item_data.menu_item_id).first()
        # if not menu_item or not menu_item.is_available:
        #     raise HTTPException(status_code=400, detail=f"Món ăn ID {item_data.menu_item_id} đã hết hoặc không tồn tại!")
        
        # Giả lập giá món tại thời điểm gọi (lấy từ menu)
        unit_price = 50000  # Thay bằng menu_item.price thực tế từ database của bạn

        order_item = OrderItem(
            order_id=new_order.id,
            menu_item_id=item_data.menu_item_id,
            quantity=item_data.quantity,
            unit_price=unit_price,
            status="pending",
            note=item_data.note
        )
        db.add(order_item)
        db.commit()
        db.refresh(order_item)

        # Thêm các tùy chọn (options/toppings) nếu có
        for opt_data in item_data.options:
            extra_price = 10000  # Lấy giá option thực tế từ database
            item_option = OrderItemOption(
                order_item_id=order_item.id,
                option_id=opt_data.option_id,
                extra_price=extra_price
            )
            db.add(item_option)
            total_amount += extra_price * item_data.quantity

        total_amount += unit_price * item_data.quantity

    db.commit()
    return success_response(request, message="Mở order thành công", data={"order_id": new_order.id})


@router.post("/{order_id}/items", summary="Thêm món (gọi thêm) vào order hiện tại")
def add_items_to_order(order_id: int, payload: list[OrderItemCreate], request: Request, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id, Order.status == "open").first()
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy order đang mở!")

    added_items = []
    for item_data in payload:
        # Kiểm tra chặn món hết (nếu có trường is_available)
        # ...

        unit_price = 50000  # Lấy giá chuẩn từ menu tại thời điểm gọi
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item_data.menu_item_id,
            quantity=item_data.quantity,
            unit_price=unit_price,
            status="pending",
            note=item_data.note
        )
        db.add(order_item)
        db.commit()
        db.refresh(order_item)

        for opt_data in item_data.options:
            extra_price = 10000
            item_option = OrderItemOption(
                order_item_id=order_item.id,
                option_id=opt_data.option_id,
                extra_price=extra_price
            )
            db.add(item_option)

        db.commit()
        added_items.append(order_item.id)

    return success_response(request, message="Thêm món thành công", data={"added_item_ids": added_items})


@router.get("/{order_id}/subtotal", summary="Tính tạm tính tổng tiền đơn hàng")
def get_order_subtotal(order_id: int, request: Request, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy order!")

    subtotal = 0
    for item in order.items:
        # Bỏ qua các món đã huỷ
        if item.status == "cancelled":
            continue
        
        item_total = float(item.unit_price) * item.quantity
        # Cộng thêm tiền options/toppings của món đó
        for opt in item.options:
            item_total += float(opt.extra_price) * item.quantity
        
        subtotal += item_total

    return success_response(request, message="Tính tạm tính thành công", data={"order_id": order_id, "subtotal": subtotal})