"""Telegram Bot Handlers"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import settings
from api_client import api
from keyboards import (
    main_menu,
    accounts_menu,
    account_detail,
    strategies_menu,
    strategy_detail,
    markets_menu,
    trade_confirm,
    alerts_menu,
)

logger = logging.getLogger(__name__)
router = Router()

# Auth state
authenticated_users: set[int] = set()


class TradeStates(StatesGroup):
    selecting_account = State()
    entering_market = State()
    entering_side = State()
    entering_price = State()
    entering_shares = State()
    confirming = State()


def is_authorized(user_id: int) -> bool:
    """Check if user is authorized"""
    # If no password set, all users are allowed
    if not settings.bot_password:
        return True
    
    # Check if user is in authorized list or authenticated
    if settings.authorized_user_ids and user_id in settings.authorized_user_ids:
        return True
    
    return user_id in authenticated_users


# ===== Commands =====

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command"""
    if not is_authorized(message.from_user.id):
        await message.answer("🔐 Please authenticate with /auth <password>")
        return
    
    await message.answer(
        "🚀 **Predict Trading System**\n\n"
        "Welcome! Use the menu below to navigate.",
        reply_markup=main_menu(),
        parse_mode="Markdown",
    )


@router.message(Command("auth"))
async def cmd_auth(message: Message):
    """Handle /auth command"""
    parts = message.text.split(maxsplit=1)
    
    if len(parts) < 2:
        await message.answer("Usage: /auth <password>")
        return
    
    password = parts[1].strip()
    
    if password == settings.bot_password:
        authenticated_users.add(message.from_user.id)
        await message.answer("✅ Authenticated!", reply_markup=main_menu())
    else:
        await message.answer("❌ Wrong password")


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Handle /stats command"""
    if not is_authorized(message.from_user.id):
        await message.answer("🔐 Please authenticate first")
        return
    
    try:
        stats = await api.get_stats()
        await message.answer(
            f"📊 **Dashboard**\n\n"
            f"👥 Accounts: {stats['active_accounts']}/{stats['total_accounts']}\n"
            f"📈 Trades (24h): {stats['total_trades_24h']}\n"
            f"💰 PnL (24h): ${stats['total_pnl_24h']:.2f}\n"
            f"🎯 Strategies: {stats['active_strategies']}\n"
            f"🔔 Alerts: {stats['pending_alerts']}",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        await message.answer(f"❌ Error: {e}")


# ===== Menu Handlers =====

@router.message(F.text == "📊 Dashboard")
async def menu_dashboard(message: Message):
    if not is_authorized(message.from_user.id):
        return
    await cmd_stats(message)


@router.message(F.text == "👥 Accounts")
async def menu_accounts(message: Message):
    if not is_authorized(message.from_user.id):
        return
    
    try:
        accounts = await api.list_accounts()
        if not accounts:
            await message.answer("No accounts found.")
            return
        
        await message.answer(
            "👥 **Accounts**\n\nSelect an account:",
            reply_markup=accounts_menu(accounts),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Failed to list accounts: {e}")
        await message.answer(f"❌ Error: {e}")


@router.message(F.text == "📈 Markets")
async def menu_markets(message: Message):
    if not is_authorized(message.from_user.id):
        return
    
    try:
        markets = await api.list_markets(limit=10)
        if not markets:
            await message.answer("No markets found.")
            return
        
        text = "📈 **Top Markets**\n\n"
        for m in markets[:10]:
            text += f"• {m['question'][:40]}...\n"
            text += f"  YES: {m['yes_price']:.2f} | NO: {m['no_price']:.2f}\n\n"
        
        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Failed to list markets: {e}")
        await message.answer(f"❌ Error: {e}")


@router.message(F.text == "🎯 Strategies")
async def menu_strategies(message: Message):
    if not is_authorized(message.from_user.id):
        return
    
    try:
        strategies = await api.list_strategies()
        if not strategies:
            await message.answer("No strategies configured.")
            return
        
        await message.answer(
            "🎯 **Strategies**\n\nSelect a strategy:",
            reply_markup=strategies_menu(strategies),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Failed to list strategies: {e}")
        await message.answer(f"❌ Error: {e}")


@router.message(F.text == "🔔 Alerts")
async def menu_alerts(message: Message):
    if not is_authorized(message.from_user.id):
        return
    
    try:
        alerts = await api.list_alerts(unread_only=True)
        if not alerts:
            await message.answer("✅ No unread alerts")
            return
        
        await message.answer(
            f"🔔 **Alerts** ({len(alerts)} unread)\n\nSelect to view:",
            reply_markup=alerts_menu(alerts),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Failed to list alerts: {e}")
        await message.answer(f"❌ Error: {e}")


@router.message(F.text == "💹 Trade")
async def menu_trade(message: Message, state: FSMContext):
    if not is_authorized(message.from_user.id):
        return
    
    try:
        accounts = await api.list_accounts()
        if not accounts:
            await message.answer("No accounts available for trading.")
            return
        
        # Store accounts in state
        await state.update_data(accounts=accounts)
        await state.set_state(TradeStates.selecting_account)
        
        text = "💹 **New Trade**\n\nSelect account:\n\n"
        for i, acc in enumerate(accounts, 1):
            status = "✅" if acc.get("active") else "❌"
            text += f"{i}. {status} [{acc['platform']}] {acc['name']}\n"
        
        text += "\nReply with account number:"
        await message.answer(text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Failed to start trade: {e}")
        await message.answer(f"❌ Error: {e}")


# ===== Callback Handlers =====

@router.callback_query(F.data.startswith("menu:"))
async def callback_menu(callback: CallbackQuery):
    if not is_authorized(callback.from_user.id):
        return
    
    menu = callback.data.split(":")[1]
    
    if menu == "main":
        await callback.message.edit_text("Main menu - use buttons below")
    elif menu == "accounts":
        accounts = await api.list_accounts()
        await callback.message.edit_text(
            "👥 **Accounts**\n\nSelect an account:",
            reply_markup=accounts_menu(accounts),
            parse_mode="Markdown",
        )
    elif menu == "strategies":
        strategies = await api.list_strategies()
        await callback.message.edit_text(
            "🎯 **Strategies**\n\nSelect a strategy:",
            reply_markup=strategies_menu(strategies),
            parse_mode="Markdown",
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("acc:"))
async def callback_account(callback: CallbackQuery):
    if not is_authorized(callback.from_user.id):
        return
    
    _, platform, account_id = callback.data.split(":")
    
    try:
        account = await api.get_account(platform, account_id)
        
        text = (
            f"👤 **{account['name']}**\n\n"
            f"Platform: {platform}\n"
            f"Address: `{account['address'][:10]}...{account['address'][-6:]}`\n"
            f"Status: {'✅ Active' if account['active'] else '❌ Inactive'}\n"
            f"Tags: {', '.join(account.get('tags', [])) or 'None'}\n"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=account_detail(platform, account_id, account['active']),
            parse_mode="Markdown",
        )
    except Exception as e:
        await callback.answer(f"Error: {e}", show_alert=True)


@router.callback_query(F.data.startswith("toggle:"))
async def callback_toggle_account(callback: CallbackQuery):
    if not is_authorized(callback.from_user.id):
        return
    
    _, platform, account_id = callback.data.split(":")
    
    try:
        account = await api.get_account(platform, account_id)
        new_status = not account['active']
        await api.toggle_account(platform, account_id, new_status)
        
        status_text = "activated" if new_status else "deactivated"
        await callback.answer(f"Account {status_text}!", show_alert=True)
        
        # Refresh view
        account = await api.get_account(platform, account_id)
        text = (
            f"👤 **{account['name']}**\n\n"
            f"Platform: {platform}\n"
            f"Address: `{account['address'][:10]}...{account['address'][-6:]}`\n"
            f"Status: {'✅ Active' if account['active'] else '❌ Inactive'}\n"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=account_detail(platform, account_id, account['active']),
            parse_mode="Markdown",
        )
    except Exception as e:
        await callback.answer(f"Error: {e}", show_alert=True)


@router.callback_query(F.data.startswith("pos:"))
async def callback_positions(callback: CallbackQuery):
    if not is_authorized(callback.from_user.id):
        return
    
    _, platform, account_id = callback.data.split(":")
    
    try:
        positions = await api.get_positions(platform, account_id)
        
        if not positions:
            await callback.answer("No positions", show_alert=True)
            return
        
        text = "📊 **Positions**\n\n"
        for p in positions[:10]:
            text += f"• {p.get('market_id', 'Unknown')[:20]}...\n"
            text += f"  {p.get('side', '?').upper()}: {p.get('shares', 0)} @ {p.get('avg_price', 0):.3f}\n\n"
        
        await callback.message.answer(text, parse_mode="Markdown")
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Error: {e}", show_alert=True)


@router.callback_query(F.data.startswith("strat:"))
async def callback_strategy(callback: CallbackQuery):
    if not is_authorized(callback.from_user.id):
        return
    
    _, strategy_id = callback.data.split(":")
    
    try:
        strategies = await api.list_strategies()
        strategy = next((s for s in strategies if s['id'] == strategy_id), None)
        
        if not strategy:
            await callback.answer("Strategy not found", show_alert=True)
            return
        
        text = (
            f"🎯 **{strategy['name']}**\n\n"
            f"Type: {strategy['type']}\n"
            f"Status: {'✅ Enabled' if strategy['enabled'] else '❌ Disabled'}\n\n"
            f"Config:\n```json\n{strategy.get('config', {})}\n```"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=strategy_detail(strategy_id, strategy['enabled']),
            parse_mode="Markdown",
        )
    except Exception as e:
        await callback.answer(f"Error: {e}", show_alert=True)


@router.callback_query(F.data.startswith("strat_toggle:"))
async def callback_toggle_strategy(callback: CallbackQuery):
    if not is_authorized(callback.from_user.id):
        return
    
    _, strategy_id = callback.data.split(":")
    
    try:
        strategies = await api.list_strategies()
        strategy = next((s for s in strategies if s['id'] == strategy_id), None)
        
        if not strategy:
            await callback.answer("Strategy not found", show_alert=True)
            return
        
        new_status = not strategy['enabled']
        await api.toggle_strategy(strategy_id, new_status)
        
        status_text = "enabled" if new_status else "disabled"
        await callback.answer(f"Strategy {status_text}!", show_alert=True)
        
        # Refresh
        await callback_strategy(callback)
    except Exception as e:
        await callback.answer(f"Error: {e}", show_alert=True)


@router.callback_query(F.data.startswith("alert:"))
async def callback_alert(callback: CallbackQuery):
    if not is_authorized(callback.from_user.id):
        return
    
    _, alert_id = callback.data.split(":")
    
    try:
        await api.mark_alert_read(alert_id)
        await callback.answer("Marked as read")
    except Exception as e:
        await callback.answer(f"Error: {e}", show_alert=True)


@router.callback_query(F.data == "alerts:read_all")
async def callback_read_all_alerts(callback: CallbackQuery):
    if not is_authorized(callback.from_user.id):
        return
    
    try:
        await api.mark_all_read()
        await callback.answer("All alerts marked as read", show_alert=True)
        await callback.message.edit_text("✅ No unread alerts")
    except Exception as e:
        await callback.answer(f"Error: {e}", show_alert=True)


# ===== Trade Flow =====

@router.message(TradeStates.selecting_account)
async def trade_select_account(message: Message, state: FSMContext):
    if not is_authorized(message.from_user.id):
        return
    
    try:
        num = int(message.text.strip())
        data = await state.get_data()
        accounts = data.get("accounts", [])
        
        if num < 1 or num > len(accounts):
            await message.answer("Invalid number. Try again:")
            return
        
        account = accounts[num - 1]
        await state.update_data(
            selected_account=account,
            account_id=account['id'],
            platform=account['platform'],
        )
        await state.set_state(TradeStates.entering_market)
        
        await message.answer(
            f"Selected: **{account['name']}**\n\n"
            "Enter market ID:",
            parse_mode="Markdown",
        )
    except ValueError:
        await message.answer("Please enter a number:")


@router.message(TradeStates.entering_market)
async def trade_enter_market(message: Message, state: FSMContext):
    if not is_authorized(message.from_user.id):
        return
    
    market_id = message.text.strip()
    await state.update_data(market_id=market_id)
    await state.set_state(TradeStates.entering_side)
    
    await message.answer("Enter side (yes/no):")


@router.message(TradeStates.entering_side)
async def trade_enter_side(message: Message, state: FSMContext):
    if not is_authorized(message.from_user.id):
        return
    
    side = message.text.strip().lower()
    if side not in ("yes", "no"):
        await message.answer("Please enter 'yes' or 'no':")
        return
    
    await state.update_data(side=side)
    await state.set_state(TradeStates.entering_price)
    
    await message.answer("Enter price (0.01 - 0.99):")


@router.message(TradeStates.entering_price)
async def trade_enter_price(message: Message, state: FSMContext):
    if not is_authorized(message.from_user.id):
        return
    
    try:
        price = float(message.text.strip())
        if not (0.01 <= price <= 0.99):
            await message.answer("Price must be between 0.01 and 0.99:")
            return
        
        await state.update_data(price=price)
        await state.set_state(TradeStates.entering_shares)
        
        await message.answer("Enter shares amount:")
    except ValueError:
        await message.answer("Please enter a valid number:")


@router.message(TradeStates.entering_shares)
async def trade_enter_shares(message: Message, state: FSMContext):
    if not is_authorized(message.from_user.id):
        return
    
    try:
        shares = float(message.text.strip())
        if shares <= 0:
            await message.answer("Shares must be positive:")
            return
        
        await state.update_data(shares=shares)
        data = await state.get_data()
        
        # Calculate cost
        cost = data['price'] * shares
        
        text = (
            f"📝 **Trade Summary**\n\n"
            f"Account: {data['selected_account']['name']}\n"
            f"Market: {data['market_id'][:30]}...\n"
            f"Side: {data['side'].upper()}\n"
            f"Price: {data['price']}\n"
            f"Shares: {shares}\n"
            f"Cost: ~${cost:.2f}\n\n"
            f"⚠️ Confirm this trade?"
        )
        
        await state.set_state(TradeStates.confirming)
        await message.answer(
            text,
            reply_markup=trade_confirm(
                data['account_id'],
                data['market_id'],
                data['side'],
                data['price'],
                shares,
            ),
            parse_mode="Markdown",
        )
    except ValueError:
        await message.answer("Please enter a valid number:")


@router.callback_query(F.data.startswith("trade_confirm:"))
async def callback_trade_confirm(callback: CallbackQuery, state: FSMContext):
    if not is_authorized(callback.from_user.id):
        return
    
    parts = callback.data.split(":")
    account_id = parts[1]
    market_id = parts[2]
    side = parts[3]
    price = float(parts[4])
    shares = float(parts[5])
    
    try:
        result = await api.execute_trade(
            account_id=account_id,
            market_id=market_id,
            side=side,
            price=price,
            shares=shares,
            confirm=True,
        )
        
        await state.clear()
        await callback.message.edit_text(
            f"✅ **Trade Submitted**\n\n"
            f"Status: {result.get('status', 'submitted')}\n"
            f"Message: {result.get('message', '')}\n"
            f"Order: {result.get('order_hash', 'N/A')[:20]}...",
            parse_mode="Markdown",
        )
        await callback.answer("Trade submitted!")
    except Exception as e:
        await callback.answer(f"Trade failed: {e}", show_alert=True)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Cancel current operation"""
    await state.clear()
    await message.answer("Cancelled", reply_markup=main_menu())
