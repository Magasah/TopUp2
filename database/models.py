from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    id: Optional[int]
    tg_id: int
    username: Optional[str]
    first_name: Optional[str]
    language: str
    joined_at: Optional[datetime]
    last_active: Optional[datetime]


@dataclass
class Game:
    id: int
    name: str
    emoji: Optional[str]
    cover_path: Optional[str]
    is_active: int


@dataclass
class Product:
    id: int
    game_id: int
    label: str
    price_tjs: int
    is_popular: int
    is_best_value: int
    is_active: int
    sort_order: int


@dataclass
class Order:
    id: Optional[int]
    user_tg_id: int
    username: Optional[str]
    game_name: Optional[str]
    product_label: Optional[str]
    price_tjs: Optional[int]
    game_account_id: Optional[str]
    payment_method: Optional[str]
    receipt_file_id: Optional[str]
    status: str
    created_at: Optional[datetime]
    completed_at: Optional[datetime]


@dataclass
class Review:
    id: Optional[int]
    order_id: Optional[int]
    user_tg_id: int
    text: str
    status: str
    channel_msg_id: Optional[int]
    created_at: Optional[datetime]
