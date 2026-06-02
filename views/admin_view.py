import sys, os
_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import flet as ft
from models.models import (
    load_users, delete_user, update_user_role,
    load_listings, save_listings,
    load_bookings, update_booking_status,
    ROLE_ADMIN, ROLE_OWNER, ROLE_GUEST,
)

ACCENT      = "#7C3AED"
ACCENT_SOFT = "#4C1D95"
BG          = "#0F0F1A"
SURFACE     = "#1A1A2E"
SURFACE2    = "#16213E"
BORDER      = "#2D2D4E"
TEXT        = "#E2E8F0"
TEXT_MUTED  = "#94A3B8"
SUCCESS     = "#22C55E"
DANGER      = "#EF4444"
WARNING     = "#F59E0B"

ROLE_LABELS = {ROLE_ADMIN: "Адмін", ROLE_OWNER: "Власник", ROLE_GUEST: "Гість"}
ROLE_COLORS = {ROLE_ADMIN: ACCENT, ROLE_OWNER: "#0D9488", ROLE_GUEST: "#3B82F6"}

STATUS_COLORS = {
    "confirmed": SUCCESS, "pending": WARNING,
    "cancelled": DANGER,  "completed": TEXT_MUTED,
}


def _clr(hex_color):
    return ft.Colors.with_opacity(1, hex_color)

def _badge(text, bg):
    return ft.Container(
        ft.Text(text, size=11, color="#FFFFFF", weight=ft.FontWeight.W_600),
        bgcolor=bg, border_radius=20,
        padding=ft.Padding.symmetric(horizontal=10, vertical=3),
    )

def _divider():
    return ft.Divider(height=1, color=BORDER)

def _section_title(icon, label):
    return ft.Row([
        ft.Container(
            ft.Icon(icon, color=ACCENT, size=20),
            bgcolor=ACCENT_SOFT, border_radius=8, padding=8,
        ),
        ft.Text(label, size=17, weight=ft.FontWeight.BOLD, color=TEXT),
    ], spacing=10)


def admin_home_view(page: ft.Page) -> ft.View:

    def _stats():
        users    = load_users()
        listings = load_listings()
        bookings = load_bookings()
        revenue  = sum(b["total_price"] for b in bookings.values()
                       if b["status"] in ("confirmed","completed"))
        confirmed = sum(1 for b in bookings.values() if b["status"]=="confirmed")
        active_l  = sum(1 for l in listings.values() if l.get("is_active"))

        def card(icon, label, value, color):
            return ft.Container(
                ft.Column([
                    ft.Container(
                        ft.Icon(icon, color=color, size=24),
                        bgcolor=ft.Colors.with_opacity(0.15, color),
                        border_radius=10, padding=10,
                    ),
                    ft.Text(str(value), size=24, weight=ft.FontWeight.BOLD,
                            color=color),
                    ft.Text(label, size=11, color=TEXT_MUTED),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=20, border_radius=14, bgcolor=SURFACE,
                border=ft.Border.all(1, BORDER),
                shadow=ft.BoxShadow(blur_radius=12,
                    color=ft.Colors.with_opacity(0.3, "#000000")),
                width=160,
            )
        return ft.Row([
            card(ft.Icons.PEOPLE_ALT, "Користувачів", len(users), "#818CF8"),
            card(ft.Icons.HOME_WORK,  "Оголошень",    active_l,   "#34D399"),
            card(ft.Icons.BOOK_ONLINE,"Підтверджених", confirmed,  "#60A5FA"),
            card(ft.Icons.PAYMENTS,   "Дохід (₴)",    f"{revenue:.0f}", "#A78BFA"),
        ],
        wrap=True, spacing=12)

    def _users_table():
        fresh = load_users()
        rows  = []

        for uname, u in fresh.items():
            is_admin = u["role"] == ROLE_ADMIN

            def mk_role(un, cur):
                roles = [ROLE_GUEST, ROLE_OWNER, ROLE_ADMIN]
                next_role = roles[(roles.index(cur) + 1) % len(roles)]
                if cur == ROLE_ADMIN:
                    next_role = ROLE_ADMIN

                def do(ev):
                    if cur == ROLE_ADMIN:
                        return
                    update_user_role(un, next_role)
                    page.go("/home")
                return do

            def mk_del(un, role):
                def do(ev):
                    if role == ROLE_ADMIN:
                        return



                    def confirm(ev2):
                        delete_user(un)
                        dlg.open = False
                        page.update()
                        page.go("/home")



                    def cancel(ev2):
                        dlg.open = False
                        page.update()



                    dlg = ft.AlertDialog(
                        modal=True,
                        title=ft.Text("Видалити користувача?", color=TEXT),
                        content=ft.Text(
                            f"«{un}» буде видалено. Його бронювання скасуються, "
                            f"оголошення деактивуються.",
                            color=TEXT_MUTED),
                        bgcolor=SURFACE,
                        actions=[
                            ft.TextButton("Скасувати", on_click=cancel,
                                style=ft.ButtonStyle(color=TEXT_MUTED)),
                            ft.FilledButton("Видалити",
                                style=ft.ButtonStyle(bgcolor=DANGER),
                                on_click=confirm),
                        ],
                    )
                    page.overlay.append(dlg)
                    dlg.open = True
                    page.update()
                return do

            rows.append(ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(uname, color=TEXT,
                                        weight=ft.FontWeight.W_600)),
                    ft.DataCell(ft.Text(u.get("full_name","—"), color=TEXT_MUTED)),
                    ft.DataCell(ft.Text(u.get("email","—"), color=TEXT_MUTED)),
                    ft.DataCell(_badge(
                        ROLE_LABELS.get(u["role"], u["role"]),
                        ROLE_COLORS.get(u["role"], BORDER))),
                    ft.DataCell(ft.Row([
                        ft.IconButton(
                            ft.Icons.SWAP_HORIZ,
                            icon_color=WARNING if not is_admin else BORDER,
                            icon_size=20,
                            tooltip="Змінити роль: Гість → Власник → Адмін",
                            on_click=mk_role(uname, u["role"]),
                            disabled=is_admin,
                        ),
                        ft.IconButton(
                            ft.Icons.DELETE_OUTLINE,
                            icon_color=DANGER if not is_admin else BORDER,
                            icon_size=20,
                            tooltip="Видалити користувача",
                            on_click=mk_del(uname, u["role"]),
                            disabled=is_admin,
                        ),
                    ], spacing=0)),
                ],
            ))

        return ft.DataTable(
            bgcolor=SURFACE2,
            border=ft.Border.all(1, BORDER),
            border_radius=12,
            heading_row_color=ft.Colors.with_opacity(0.5, ACCENT_SOFT),
            heading_row_height=44,
            data_row_max_height=52,
            columns=[
                ft.DataColumn(ft.Text("Логін", color=TEXT_MUTED, size=12)),
                ft.DataColumn(ft.Text("Ім'я", color=TEXT_MUTED, size=12)),
                ft.DataColumn(ft.Text("Email", color=TEXT_MUTED, size=12)),
                ft.DataColumn(ft.Text("Роль", color=TEXT_MUTED, size=12)),
                ft.DataColumn(ft.Text("Дії", color=TEXT_MUTED, size=12)),
            ],
            rows=rows,
        )

    def _listings_table():
        fresh = load_listings()
        rows  = []
        for lid, lst in fresh.items():
            def mk_toggle(l_id, cur):
                def do(ev):
                    fl = load_listings()
                    fl[l_id]["is_active"] = not cur
                    save_listings(fl)
                    page.go("/home")
                return do
            def mk_del(l_id):
                def do(ev):
                    fl = load_listings()
                    if l_id in fl:
                        del fl[l_id]
                        save_listings(fl)
                    page.go("/home")
                return do

            rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(lst["title"][:28], color=TEXT)),
                ft.DataCell(ft.Text(lst["city"], color=TEXT_MUTED)),
                ft.DataCell(ft.Text(lst["owner"], color=TEXT_MUTED)),
                ft.DataCell(ft.Text(lst["property_type"], color=TEXT_MUTED)),
                ft.DataCell(ft.Text(f"₴{lst['price_per_night']:.0f}", color=TEXT)),
                ft.DataCell(_badge("Активне" if lst["is_active"] else "Неакт.", SUCCESS   if lst["is_active"] else DANGER)),
                ft.DataCell(ft.Row([
                    ft.IconButton(
                        ft.Icons.TOGGLE_ON if lst["is_active"] else ft.Icons.TOGGLE_OFF,
                        icon_color=SUCCESS if lst["is_active"] else DANGER,
                        icon_size=20,
                        on_click=mk_toggle(lid, lst["is_active"])),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=DANGER, icon_size=20, on_click=mk_del(lid)),
                ], spacing=0)),
            ]))
        return ft.DataTable(
            bgcolor=SURFACE2, border=ft.Border.all(1, BORDER), border_radius=12,
            heading_row_color=ft.Colors.with_opacity(0.5, ACCENT_SOFT),
            heading_row_height=44, data_row_max_height=52,
            columns=[ft.DataColumn(ft.Text(t, color=TEXT_MUTED, size=12))
                     for t in ["Назва","Місто","Власник","Тип","Ціна","Статус","Дії"]],
            rows=rows,
        )

    def _bookings_table():
        fresh_b = load_bookings()
        fresh_l = load_listings()
        rows    = []
        for bid, b in sorted(fresh_b.items(), key=lambda x: x[1]["created_at"], reverse=True):
            lst = fresh_l.get(b["listing_id"], {})
            def mk_cancel(bk_id, st):
                def do(ev):
                    update_booking_status(bk_id, "cancelled", "refunded")
                    page.go("/home")
                return do


            can = b["status"] not in ("cancelled","completed")
            rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(bid[-8:], color=TEXT_MUTED, size=11)),
                ft.DataCell(ft.Text(lst.get("title","—")[:20], color=TEXT)),
                ft.DataCell(ft.Text(b["guest_username"], color=TEXT_MUTED)),
                ft.DataCell(ft.Text(f"{b['check_in']} → {b['check_out']}", color=TEXT_MUTED)),
                ft.DataCell(ft.Text(f"₴{b['total_price']:.0f}", color=TEXT)),
                ft.DataCell(_badge(b["status"].upper(),
                STATUS_COLORS.get(b["status"], BORDER))),
                ft.DataCell(ft.IconButton(ft.Icons.CANCEL_OUTLINED, icon_color=DANGER if can else BORDER, icon_size=20, on_click=mk_cancel(bid, b["status"]), disabled=not can)),
            ]))


        return ft.DataTable(
            bgcolor=SURFACE2, border=ft.Border.all(1, BORDER), border_radius=12,
            heading_row_color=ft.Colors.with_opacity(0.5, ACCENT_SOFT),
            heading_row_height=44,
            data_row_max_height=52,
            columns=[ft.DataColumn(ft.Text(t, color=TEXT_MUTED, size=12))
                     for t in ["ID","Помешкання","Гість","Дати","Сума","Статус","Дія"]],
            rows=rows,
        )

    def _section(title, icon, table_fn):
        return ft.Container(
            ft.Column([
                _section_title(icon, title),
                _divider(),
                ft.Row([table_fn()], scroll=ft.ScrollMode.ADAPTIVE),
            ], spacing=12),
            padding=20, border_radius=14, bgcolor=SURFACE,
            border=ft.Border.all(1, BORDER),
            margin=ft.Margin.only(bottom=16),
        )

    async def logout(e):
        page.session.store.clear()
        await page.push_route("/login")

    return ft.View(
        route="/home",
        bgcolor=BG,
        scroll=ft.ScrollMode.ADAPTIVE,
        appbar=ft.AppBar(
            leading=ft.Container(
                ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS, color="#FFFFFF", size=22),
                bgcolor=ACCENT, border_radius=8, padding=6, margin=ft.Margin.only(left=8)),
            title=ft.Text("Панель адміністратора", color=TEXT, weight=ft.FontWeight.BOLD),
            bgcolor=SURFACE,
            actions=[
                ft.IconButton(ft.Icons.REFRESH, icon_color=TEXT_MUTED, tooltip="Оновити", on_click=lambda e: page.go("/home")),
                ft.IconButton(ft.Icons.LOGOUT, icon_color=DANGER, tooltip="Вийти", on_click=logout),
            ],
        ),
        controls=[
            ft.Container(
                ft.Column([
                    ft.Text("Загальна статистика", size=20, weight=ft.FontWeight.BOLD, color=TEXT),
                    _stats(),
                    ft.Container(height=8),
                    _section("Користувачі", ft.Icons.PEOPLE_ALT, _users_table),
                    _section("Оголошення",  ft.Icons.HOME_WORK,   _listings_table),
                    _section("Бронювання",  ft.Icons.BOOK_ONLINE, _bookings_table),
                ], spacing=16),
                padding=20,
            )
        ],
    )
