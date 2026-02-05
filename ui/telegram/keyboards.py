"""Telegram Keyboards"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def main_menu() -> ReplyKeyboardMarkup:
    """Main menu keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Dashboard"), KeyboardButton(text="👥 Accounts")],
            [KeyboardButton(text="📈 Markets"), KeyboardButton(text="💹 Trade")],
            [KeyboardButton(text="🎯 Strategies"), KeyboardButton(text="🔔 Alerts")],
        ],
        resize_keyboard=True,
    )


def accounts_menu(accounts: list) -> InlineKeyboardMarkup:
    """Accounts list keyboard"""
    buttons = []
    for acc in accounts:
        status = "✅" if acc.get("active") else "❌"
        platform = acc.get("platform", "?")[:1].upper()
        buttons.append([InlineKeyboardButton(
            text=f"{status} [{platform}] {acc['name']}",
            callback_data=f"acc:{acc['platform']}:{acc['id']}",
        )])
    
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def account_detail(platform: str, account_id: str, active: bool) -> InlineKeyboardMarkup:
    """Account detail keyboard"""
    toggle_text = "🔴 Deactivate" if active else "🟢 Activate"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Positions", callback_data=f"pos:{platform}:{account_id}")],
        [InlineKeyboardButton(text=toggle_text, callback_data=f"toggle:{platform}:{account_id}")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="menu:accounts")],
    ])


def strategies_menu(strategies: list) -> InlineKeyboardMarkup:
    """Strategies list keyboard"""
    buttons = []
    for s in strategies:
        status = "✅" if s.get("enabled") else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{status} {s['name']} ({s['type']})",
            callback_data=f"strat:{s['id']}",
        )])
    
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def strategy_detail(strategy_id: str, enabled: bool) -> InlineKeyboardMarkup:
    """Strategy detail keyboard"""
    toggle_text = "🔴 Disable" if enabled else "🟢 Enable"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle_text, callback_data=f"strat_toggle:{strategy_id}")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="menu:strategies")],
    ])


def markets_menu(markets: list) -> InlineKeyboardMarkup:
    """Markets list keyboard"""
    buttons = []
    for m in markets[:10]:  # Limit to 10
        price = f"Y:{m['yes_price']:.2f} N:{m['no_price']:.2f}"
        question = m['question'][:30] + "..." if len(m['question']) > 30 else m['question']
        buttons.append([InlineKeyboardButton(
            text=f"📊 {question}",
            callback_data=f"market:{m['platform']}:{m['market_id'][:20]}",
        )])
    
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def trade_confirm(account_id: str, market_id: str, side: str, price: float, shares: float) -> InlineKeyboardMarkup:
    """Trade confirmation keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Confirm", callback_data=f"trade_confirm:{account_id}:{market_id}:{side}:{price}:{shares}"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="menu:main"),
        ],
    ])


def alerts_menu(alerts: list) -> InlineKeyboardMarkup:
    """Alerts list keyboard"""
    buttons = []
    for a in alerts[:10]:
        icon = "🔔" if not a.get("read") else "✓"
        title = a['title'][:25] + "..." if len(a['title']) > 25 else a['title']
        buttons.append([InlineKeyboardButton(
            text=f"{icon} {title}",
            callback_data=f"alert:{a['id']}",
        )])
    
    if alerts:
        buttons.append([InlineKeyboardButton(text="✓ Mark All Read", callback_data="alerts:read_all")])
    
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
