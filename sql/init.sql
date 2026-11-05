-- Tạo 17 bảng + dữ liệu mẫu cho hệ thống quản lý nhà hàng.
-- Docker: tự chạy lần đầu `docker compose up` (database app_db đã được tạo sẵn).
-- MySQL cài tay / XAMPP: mở phpMyAdmin hoặc MySQL Workbench rồi chạy cả file này.
-- Đổi cấu trúc bảng: sửa file này, rồi mỗi người chạy `docker compose down -v` và `docker compose up -d`
-- (xoá sạch dữ liệu cũ và tạo lại từ file này).

SET NAMES utf8mb4; -- để tiếng Việt không bị lỗi font

CREATE DATABASE IF NOT EXISTS app_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE app_db;

-- ==========================================================
-- M1: Xác thực và nhân sự
-- ==========================================================

CREATE TABLE IF NOT EXISTS branches (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    address VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    open_time TIME NOT NULL DEFAULT '10:00:00',
    close_time TIME NOT NULL DEFAULT '22:00:00',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(30) NOT NULL UNIQUE      -- admin, manager, cashier, waiter, kitchen
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    branch_id INT NULL,                   -- NULL nếu là admin tổng
    role_id INT NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (branch_id) REFERENCES branches(id),
    FOREIGN KEY (role_id) REFERENCES roles(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================================
-- M2: Menu và bàn
-- ==========================================================

CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    sort_order INT NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS menu_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category_id INT NOT NULL,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    image_url VARCHAR(255),
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS menu_item_options (   -- size, topping...
    id INT AUTO_INCREMENT PRIMARY KEY,
    menu_item_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    extra_price DECIMAL(10,2) NOT NULL DEFAULT 0,
    FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS dining_tables (
    id INT AUTO_INCREMENT PRIMARY KEY,
    branch_id INT NOT NULL,
    table_number VARCHAR(20) NOT NULL,
    capacity INT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'available',   -- available / occupied / reserved
    UNIQUE (branch_id, table_number),
    FOREIGN KEY (branch_id) REFERENCES branches(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================================
-- M3: Web khách và đặt bàn
-- ==========================================================

CREATE TABLE IF NOT EXISTS customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL UNIQUE,
    email VARCHAR(100),
    password_hash VARCHAR(255) NULL,      -- NULL nếu khách không đăng ký tài khoản
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS reservations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,     -- mã để khách tra cứu / huỷ
    branch_id INT NOT NULL,
    table_id INT NULL,                    -- NULL đến khi xếp bàn
    customer_id INT NULL,                 -- NULL nếu khách vãng lai
    guest_name VARCHAR(100) NOT NULL,
    guest_phone VARCHAR(20) NOT NULL,
    party_size INT NOT NULL,
    reserved_at DATETIME NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',   -- pending / confirmed / seated / cancelled / no_show
    note VARCHAR(255),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_reservations_branch_time (branch_id, reserved_at),
    FOREIGN KEY (branch_id) REFERENCES branches(id),
    FOREIGN KEY (table_id) REFERENCES dining_tables(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================================
-- M4: Order và bếp
-- ==========================================================

CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    branch_id INT NOT NULL,
    table_id INT NOT NULL,
    reservation_id INT NULL,              -- NULL nếu khách đến không đặt trước
    waiter_id INT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'open',      -- open / sent / served / paid / cancelled
    note VARCHAR(255),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at DATETIME NULL,
    INDEX idx_orders_branch_status (branch_id, status),
    FOREIGN KEY (branch_id) REFERENCES branches(id),
    FOREIGN KEY (table_id) REFERENCES dining_tables(id),
    FOREIGN KEY (reservation_id) REFERENCES reservations(id),
    FOREIGN KEY (waiter_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    menu_item_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,    -- lưu giá tại thời điểm gọi
    status VARCHAR(20) NOT NULL DEFAULT 'pending',   -- pending / cooking / done / served / cancelled
    note VARCHAR(255),
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS order_item_options (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_item_id INT NOT NULL,
    option_id INT NOT NULL,
    extra_price DECIMAL(10,2) NOT NULL DEFAULT 0,    -- lưu giá tại thời điểm gọi
    FOREIGN KEY (order_item_id) REFERENCES order_items(id),
    FOREIGN KEY (option_id) REFERENCES menu_item_options(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================================
-- M5: Thanh toán, kho, báo cáo
-- ==========================================================

CREATE TABLE IF NOT EXISTS vouchers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(30) NOT NULL UNIQUE,
    discount_type VARCHAR(10) NOT NULL,              -- percent / amount
    discount_value DECIMAL(10,2) NOT NULL,
    min_order_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    usage_limit INT NULL,                            -- NULL = không giới hạn
    used_count INT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL UNIQUE,
    cashier_id INT NOT NULL,
    voucher_id INT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    discount_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    total_amount DECIMAL(10,2) NOT NULL,
    method VARCHAR(20) NOT NULL,                     -- cash / card / transfer
    status VARCHAR(20) NOT NULL DEFAULT 'paid',      -- paid / refunded
    paid_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (cashier_id) REFERENCES users(id),
    FOREIGN KEY (voucher_id) REFERENCES vouchers(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ingredients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    unit VARCHAR(20) NOT NULL                        -- g, ml, cái...
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recipes (                 -- món dùng nguyên liệu nào, bao nhiêu
    id INT AUTO_INCREMENT PRIMARY KEY,
    menu_item_id INT NOT NULL,
    ingredient_id INT NOT NULL,
    quantity_needed DECIMAL(10,2) NOT NULL,
    UNIQUE (menu_item_id, ingredient_id),
    FOREIGN KEY (menu_item_id) REFERENCES menu_items(id),
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS branch_inventories (      -- tồn kho từng chi nhánh
    id INT AUTO_INCREMENT PRIMARY KEY,
    branch_id INT NOT NULL,
    ingredient_id INT NOT NULL,
    quantity DECIMAL(10,2) NOT NULL DEFAULT 0,
    min_quantity DECIMAL(10,2) NOT NULL DEFAULT 0,   -- dưới mức này thì cảnh báo
    UNIQUE (branch_id, ingredient_id),
    FOREIGN KEY (branch_id) REFERENCES branches(id),
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================================
-- DỮ LIỆU MẪU (Docker chỉ chạy file này lần đầu trên database mới tạo)
-- Mật khẩu của mọi tài khoản mẫu: Restaurant@123
-- ==========================================================

INSERT IGNORE INTO roles (name) VALUES
    ('admin'), ('manager'), ('cashier'), ('waiter'), ('kitchen');

INSERT INTO branches (name, address, phone) VALUES
    ('Chi nhánh Quận 1', '8/15 Lê Thánh Tôn, Quận 1, TP.HCM', '02812345678'),
    ('Chi nhánh Hà Nội', '43 Phan Kế Bình, Ba Đình, Hà Nội', '02487654321');

INSERT INTO users (branch_id, role_id, full_name, email, password_hash, phone) VALUES
    (NULL, (SELECT id FROM roles WHERE name = 'admin'),   'Quản trị viên', 'admin@restaurant.com',   '$2b$12$zS23Ph0uOpy5QPhxKAmUJ.eaOzpYJ2OMZIED54ARzwJJe9vrcFC4a', NULL),
    (1,    (SELECT id FROM roles WHERE name = 'manager'), 'Nguyễn Văn A',  'manager@restaurant.com', '$2b$12$zS23Ph0uOpy5QPhxKAmUJ.eaOzpYJ2OMZIED54ARzwJJe9vrcFC4a', '0901000001'),
    (1,    (SELECT id FROM roles WHERE name = 'cashier'), 'Trần Thị B',    'cashier@restaurant.com', '$2b$12$zS23Ph0uOpy5QPhxKAmUJ.eaOzpYJ2OMZIED54ARzwJJe9vrcFC4a', '0901000002'),
    (1,    (SELECT id FROM roles WHERE name = 'waiter'),  'Lê Văn C',      'waiter@restaurant.com',  '$2b$12$zS23Ph0uOpy5QPhxKAmUJ.eaOzpYJ2OMZIED54ARzwJJe9vrcFC4a', '0901000003'),
    (1,    (SELECT id FROM roles WHERE name = 'kitchen'), 'Phạm Thị D',    'kitchen@restaurant.com', '$2b$12$zS23Ph0uOpy5QPhxKAmUJ.eaOzpYJ2OMZIED54ARzwJJe9vrcFC4a', '0901000004');

INSERT INTO categories (name, sort_order) VALUES
    ('Pizza', 1), ('Pasta', 2), ('Salad', 3), ('Đồ uống', 4);

INSERT INTO menu_items (category_id, name, description, price) VALUES
    (1, 'Pizza Margherita', 'Pizza phủ mozzarella và cà chua', 150000),
    (1, 'Pizza Hải Sản', 'Pizza hải sản tươi', 190000),
    (2, 'Mì Ý Cua', 'Mì Ý sốt cua béo', 180000),
    (3, 'Salad Rau Củ', 'Rau củ tươi trong ngày', 90000),
    (4, 'Nước ép cam', 'Cam vắt tươi', 50000);

INSERT INTO menu_item_options (menu_item_id, name, extra_price) VALUES
    (1, 'Size L', 40000),
    (1, 'Thêm phô mai', 20000);

INSERT INTO dining_tables (branch_id, table_number, capacity) VALUES
    (1, 'A1', 2), (1, 'A2', 4), (1, 'A3', 6),
    (2, 'B1', 2), (2, 'B2', 4);

INSERT INTO ingredients (name, unit) VALUES
    ('Bột mì', 'g'), ('Phô mai mozzarella', 'g'), ('Cà chua', 'g'), ('Cua', 'g');

INSERT INTO recipes (menu_item_id, ingredient_id, quantity_needed) VALUES
    (1, 1, 200), (1, 2, 100), (1, 3, 80);

INSERT INTO branch_inventories (branch_id, ingredient_id, quantity, min_quantity) VALUES
    (1, 1, 5000, 1000), (1, 2, 3000, 500), (1, 3, 2000, 400), (1, 4, 1500, 300);

INSERT INTO vouchers (code, discount_type, discount_value, min_order_amount, start_date, end_date, usage_limit) VALUES
    ('WELCOME10', 'percent', 10, 200000, '2026-11-01', '2026-12-31', 100);
