import sys, os
_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import flet as ft
from datetime import date, timedelta
from models.models import (
    load_listings, load_bookings, save_bookings,
    is_listing_available, nights_between, generate_id,
    STATUS_CONFIRMED, PAYMENT_PAID,
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


def _listing_photo_control(listing: dict, size=84, on_click=None) -> ft.Container:
    photos = listing.get("photos", [])
    if photos:
        return ft.Container(
            content=ft.Image(src=photos[0], width=size, height=size, fit=ft.BoxFit.COVER),
            width=size,
            height=size,
            border_radius=8,
            bgcolor=SURFACE2,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            data=listing,
            ink=on_click is not None,
            tooltip="Переглянути фото" if on_click else None,
            on_click=on_click,
        )
    return ft.Container(
        content=ft.Icon(ft.Icons.APARTMENT, color=ACCENT, size=28),
        width=size,
        height=size,
        border_radius=8,
        bgcolor=SURFACE2,
    )


def _listing_card(listing: dict, on_book, on_photos) -> ft.Container:
    amenities = ", ".join(listing.get("amenities", [])) or "—"
    photos = listing.get("photos", [])
    stars = "★" * min(5, max(1, listing.get("rooms", 1)))
    return ft.Container(
        content=ft.Column([
            ft.Row([
                _listing_photo_control(listing, on_click=on_photos if photos else None),
                ft.Column([
                    ft.Text(listing["title"], size=16, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{listing['city']} · {listing['address']}", size=12, color=TEXT_MUTED),
                ], spacing=2, expand=True),
                ft.Column([
                    ft.Text(f"₴{listing['price_per_night']:.0f}/ніч", size=16, weight=ft.FontWeight.BOLD, color=ACCENT),
                    ft.Text(f"до {listing['max_guests']} гостей", size=11, color=TEXT_MUTED),
                ], horizontal_alignment=ft.CrossAxisAlignment.END, spacing=2),
            ], alignment=ft.MainAxisAlignment.START),
            ft.Row([
                ft.Text(listing["property_type"], size=12, color=TEXT_MUTED),
                ft.Text("·", color=TEXT_MUTED),
                ft.Text(f"{listing['rooms']} кімн. {stars}", size=12),
            ], spacing=6),
            ft.Text(listing.get("description", "")[:80] + "…"
                    if len(listing.get("description", "")) > 80
                    else listing.get("description", ""),
                    size=12, color=TEXT_MUTED),
            ft.Text(f"Зручності: {amenities}", size=11,color=TEXT_MUTED),
            ft.Row([
                ft.TextButton(
                    f"Фото ({len(photos)})",
                    icon=ft.Icons.PHOTO_LIBRARY,
                    data=listing,
                    on_click=on_photos,
                    visible=bool(photos),
                ),
                ft.FilledButton("Забронювати", icon=ft.Icons.BOOK_ONLINE, data=listing, on_click=on_book),
            ], alignment=ft.MainAxisAlignment.END, spacing=8),
        ], spacing=6),
        padding=16, border_radius=12,
        bgcolor=SURFACE,
        shadow=ft.BoxShadow(blur_radius=8, color=ft.Colors.with_opacity(0.08, ft.Colors.BLACK)),
        margin=ft.Margin.only(bottom=10),
    )


def guest_home_view(page: ft.Page) -> ft.View:
    user = page.session.store.get("current_user")
    listings = load_listings()
    bookings = load_bookings()
    today      = date.today()
    tomorrow   = today + timedelta(days=1)
    after_two  = tomorrow + timedelta(days=1)

    def _parse_picker_date(value, fallback):
        try:
            return date.fromisoformat(value)
        except (TypeError, ValueError):
            return fallback

    def _picker_value_to_iso(value):
        return value.date().isoformat() if hasattr(value, "date") else value.isoformat()

    def _open_date_picker(field, title, fallback):
        selected = _parse_picker_date(field.value, fallback)

        def set_date(ev):
            if ev.control.value:
                field.value = _picker_value_to_iso(ev.control.value)
                page.update()

        page.show_dialog(
            ft.DatePicker(
                value=selected,
                locale=ft.Locale("uk", "UA"),
                first_date=today,
                last_date=today + timedelta(days=365 * 2),
                current_date=selected,
                help_text=title,
                cancel_text="Скасувати",
                confirm_text="Обрати",
                error_format_text="Введіть дату у форматі РРРР-ММ-ДД",
                error_invalid_text="Дата поза доступним діапазоном",
                field_label_text=title,
                field_hint_text="РРРР-ММ-ДД",
                on_change=set_date,
            )
        )

    city_f      = ft.TextField(label="Місто", hint_text="Київ, Львів…", border_radius=10, filled=True, width=160)
    check_in_f  = ft.TextField(
        label="Заїзд",
        value=str(tomorrow),
        border_radius=10,
        filled=True,
        width=160,
        read_only=True,
        show_cursor=False,
        suffix_icon=ft.Icons.CALENDAR_MONTH,
        on_click=lambda _: _open_date_picker(check_in_f, "Оберіть дату заїзду", tomorrow),
    )
    check_out_f = ft.TextField(
        label="Виїзд",
        value=str(after_two),
        border_radius=10,
        filled=True,
        width=160,
        read_only=True,
        show_cursor=False,
        suffix_icon=ft.Icons.CALENDAR_MONTH,
        on_click=lambda _: _open_date_picker(check_out_f, "Оберіть дату виїзду", after_two),
    )
    guests_f    = ft.TextField(label="Гостей", value="1", border_radius=10, filled=True, width=80)
    type_dd     = ft.Dropdown(
        label="Тип",
        options=[ft.DropdownOption("", "Усі"),
                 ft.DropdownOption("Квартира"),
                 ft.DropdownOption("Будинок"),
                 ft.DropdownOption("Кімната")],
        value="", width=130, border_radius=10,
    )

    results_col = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, expand=True, spacing=0)
    status_txt  = ft.Text("", color=DANGER, size=13)

    def search(e=None):
        ci   = check_in_f.value.strip()
        co   = check_out_f.value.strip()
        city = city_f.value.strip().lower()
        try:
            g = int(guests_f.value)
        except ValueError:
            g = 1
        ptype = type_dd.value

        fresh = load_listings()
        fresh_b = load_bookings()
        results_col.controls.clear()
        found = 0
        for lid, lst in fresh.items():
            if not lst.get("is_active", True):
                continue
            if city and city not in lst["city"].lower():
                continue
            if ptype and lst["property_type"] != ptype:
                continue
            if lst["max_guests"] < g:
                continue
            try:
                if not is_listing_available(lid, ci, co, fresh_b):
                    continue
            except Exception:
                continue
            results_col.controls.append(
                _listing_card(lst, on_book=open_booking_dialog, on_photos=open_photos_dialog))
            found += 1

        if found == 0:
            results_col.controls.append(
                ft.Container(
                    ft.Column([
                        ft.Icon(ft.Icons.SEARCH_OFF, size=48,
                                color=TEXT_MUTED),
                        ft.Text("Нічого не знайдено",
                                color=TEXT_MUTED, size=16),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=40,
                )
            )
        page.update()

    def open_photos_dialog(e):
        lst = e.control.data
        photos = list(lst.get("photos", []))
        if not photos:
            return

        current = {"index": 0}
        main_image = ft.Image(
            src=photos[0],
            width=720,
            height=420,
            fit=ft.BoxFit.CONTAIN,
        )
        counter = ft.Text(f"1 / {len(photos)}", size=13, color=TEXT_MUTED)
        thumbs_row = ft.Row(wrap=True, spacing=8, run_spacing=8)

        def make_thumb_click(index):
            def choose_photo(ev):
                show_photo(index)
            return choose_photo

        def refresh_thumbs():
            thumbs_row.controls.clear()
            for index, src in enumerate(photos):
                selected = index == current["index"]
                thumbs_row.controls.append(
                    ft.Container(
                        content=ft.Image(
                            src=src,
                            width=68,
                            height=52,
                            fit=ft.BoxFit.COVER,
                        ),
                        width=74,
                        height=58,
                        bgcolor=SURFACE2,
                        border=ft.Border.all(2, ACCENT if selected else BORDER),
                        border_radius=6,
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                        ink=True,
                        on_click=make_thumb_click(index),
                    )
                )

        def show_photo(index):
            current["index"] = index % len(photos)
            main_image.src = photos[current["index"]]
            counter.value = f"{current['index'] + 1} / {len(photos)}"
            refresh_thumbs()
            page.update()

        def prev_photo(ev):
            show_photo(current["index"] - 1)

        def next_photo(ev):
            show_photo(current["index"] + 1)

        def close_dlg(ev):
            dlg.open = False
            page.update()

        refresh_thumbs()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.PHOTO_LIBRARY, color=ACCENT),
                ft.Text(lst["title"], weight=ft.FontWeight.BOLD),
            ], spacing=8),
            content=ft.Column([
                ft.Container(
                    content=main_image,
                    width=720,
                    height=420,
                    bgcolor=BG,
                    border_radius=8,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                ),
                ft.Row([
                    ft.IconButton(
                        ft.Icons.CHEVRON_LEFT,
                        icon_color=TEXT,
                        tooltip="Попереднє фото",
                        on_click=prev_photo,
                        visible=len(photos) > 1,
                    ),
                    counter,
                    ft.IconButton(
                        ft.Icons.CHEVRON_RIGHT,
                        icon_color=TEXT,
                        tooltip="Наступне фото",
                        on_click=next_photo,
                        visible=len(photos) > 1,
                    ),
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=18),
                thumbs_row,
            ], spacing=10, width=720, scroll=ft.ScrollMode.ADAPTIVE),
            actions=[
                ft.TextButton("Закрити", icon=ft.Icons.CLOSE, on_click=close_dlg),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def open_booking_dialog(e):
        lst = e.control.data
        lid = lst["id"]
        ci  = check_in_f.value.strip()
        co  = check_out_f.value.strip()
        try:
            g = int(guests_f.value)
        except ValueError:
            g = 1

        try:
            nights = nights_between(ci, co)
            total  = nights * lst["price_per_night"]
        except Exception:
            nights = 0
            total  = 0

        notes_f = ft.TextField(label="Побажання (необов'язково)", multiline=True, min_lines=2, max_lines=4, border_radius=10, filled=True)
        pay_group = ft.RadioGroup(
            value="card",
            content=ft.Column([
                ft.Row([ft.Radio(value="card", label=""),
                        ft.Icon(ft.Icons.CREDIT_CARD),
                        ft.Text("Банківська картка")]),
                ft.Row([ft.Radio(value="cash", label=""),
                        ft.Icon(ft.Icons.MONEY),
                        ft.Text("Готівка при заїзді")]),
            ], spacing=6),
        )
        dlg_err = ft.Text(color=DANGER, size=12)

        def confirm_booking(ev):
            bkgs = load_bookings()
            if not is_listing_available(lid, ci, co, bkgs):
                dlg_err.value = "На жаль, ці дати вже зайняті!"
                page.update()
                return

            bid = generate_id("BK")
            pay_st = PAYMENT_PAID if pay_group.value == "card" else "pending"
            bkgs[bid] = {
                "id": bid,
                "listing_id": lid,
                "guest_username": user,
                "check_in": ci,
                "check_out": co,
                "guests_count": g,
                "total_price": total,
                "status": STATUS_CONFIRMED,
                "payment_status": pay_st,
                "created_at": str(date.today()),
                "notes": notes_f.value,
            }
            save_bookings(bkgs)
            dlg.open = False
            page.update()
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Бронювання підтверджено! ID: {bid}"),
                bgcolor=SUCCESS)
            page.snack_bar.open = True
            search()

        def close_dlg(ev):
            dlg.open = False
            page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([ft.Icon(ft.Icons.BOOK_ONLINE, color=ACCENT),
            ft.Text("Підтвердження бронювання")], spacing=8),
            content=ft.Column([
                ft.Text(lst["title"], weight=ft.FontWeight.BOLD, size=15),
                ft.Text(f"{lst['city']}, {lst['address']}", size=12, color=TEXT_MUTED),
                ft.Divider(),
                ft.Row([
                    ft.Column([ft.Text("Заїзд"), ft.Text(ci, weight=ft.FontWeight.W_600)]),
                    ft.VerticalDivider(),
                    ft.Column([ft.Text("Виїзд"), ft.Text(co, weight=ft.FontWeight.W_600)]),
                    ft.VerticalDivider(),
                    ft.Column([ft.Text("Ночей"), ft.Text(str(nights), weight=ft.FontWeight.W_600)]),
                    ft.VerticalDivider(),
                    ft.Column([ft.Text("Гостей"), ft.Text(str(g), weight=ft.FontWeight.W_600)]),
                ], spacing=10),
                ft.Divider(),
                ft.Text(f"Загальна сума: ₴{total:.0f}", size=16, weight=ft.FontWeight.BOLD, color=ACCENT),
                ft.Text("Спосіб оплати:", size=13, color=TEXT_MUTED),
                pay_group,
                notes_f,
                dlg_err,
            ], spacing=10, width=380, scroll=ft.ScrollMode.ADAPTIVE),
            actions=[
                ft.TextButton("Скасувати", on_click=close_dlg),
                ft.FilledButton("Підтвердити", icon=ft.Icons.CHECK, on_click=confirm_booking),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    search()

    async def go_my_bookings(e):
        await page.push_route("/my_bookings")

    async def logout(e):
        page.session.store.clear()
        await page.push_route("/login")

    appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.HOTEL, color=ft.Colors.WHITE),
        title=ft.Text("Booking System — Пошук житла", color=TEXT),
        bgcolor=SURFACE,
        actions=[
            ft.TextButton("Мої бронювання",
                          style=ft.ButtonStyle(color=ft.Colors.WHITE),
                          on_click=go_my_bookings),
            ft.IconButton(ft.Icons.LOGOUT, icon_color=ft.Colors.WHITE, tooltip="Вийти", on_click=logout),
        ],
    )

    search_bar = ft.Container(
        content=ft.Column([
            ft.Text("Знайти помешкання", size=18,
                    weight=ft.FontWeight.BOLD),
            ft.Row([city_f, check_in_f, check_out_f,
                    guests_f, type_dd], wrap=True, spacing=10),
            ft.Row([
                ft.FilledButton("Пошук", icon=ft.Icons.SEARCH, on_click=search),
                status_txt,
            ], spacing=12),
        ], spacing=10),
        padding=16, bgcolor=BG,
        border_radius=12, margin=ft.Margin.only(bottom=12),
    )

    return ft.View(
        route="/home",
        appbar=appbar,
        bgcolor=BG,
        scroll=ft.ScrollMode.ADAPTIVE,
        controls=[
            ft.Container(
                content=ft.Column([search_bar, results_col]),
                padding=16,
            )
        ],
    )



def my_bookings_view(page: ft.Page) -> ft.View:
    user = page.session.store.get("current_user")
    bookings = load_bookings()
    listings = load_listings()

    status_colors = {
        "confirmed": SUCCESS,
        "pending":   ft.Colors.ORANGE_600,
        "cancelled": DANGER,
        "completed": ft.Colors.GREY_500,
    }
    pay_icons = {
        "paid":     (ft.Icons.CHECK_CIRCLE, SUCCESS),
        "pending":  (ft.Icons.HOURGLASS_EMPTY, ft.Colors.ORANGE_600),
        "refunded": (ft.Icons.REPLAY, ft.Colors.BLUE_400),
    }

    col = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, expand=True, spacing=8)

    my = [(bid, b) for bid, b in bookings.items()
          if b["guest_username"] == user]

    if not my:
        col.controls.append(
            ft.Container(
                ft.Column([
                    ft.Icon(ft.Icons.BOOK_OUTLINED, size=64, color=TEXT_MUTED),
                    ft.Text("У вас ще немає бронювань", size=16, color=TEXT_MUTED),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=40,
            )
        )
    else:
        for bid, b in sorted(my, key=lambda x: x[1]["created_at"], reverse=True):
            lst = listings.get(b["listing_id"], {})
            pay_icon, pay_color = pay_icons.get(b["payment_status"], (ft.Icons.HELP, ft.Colors.GREY))

            def make_cancel(bk_id):
                def cancel(ev):
                    bkgs = load_bookings()
                    if bkgs.get(bk_id):
                        bkgs[bk_id]["status"] = "cancelled"
                        bkgs[bk_id]["payment_status"] = "refunded"
                        save_bookings(bkgs)
                    page.snack_bar = ft.SnackBar(
                        ft.Text("Бронювання скасовано"),
                        bgcolor=ft.Colors.ORANGE_700)
                    page.snack_bar.open = True
                    page.go("/my_bookings")
                return cancel

            can_cancel = b["status"] not in ("cancelled", "completed")

            card = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(lst.get("title", b["listing_id"]), size=15, weight=ft.FontWeight.BOLD, expand=True),
                        ft.Text(b["status"].upper(), size=11, color=status_colors.get(b["status"], ACCENT), weight=ft.FontWeight.BOLD),
                    ]),
                    ft.Text(f"{lst.get('city', '')} · {lst.get('address', '')}", size=12, color=TEXT_MUTED),
                    ft.Divider(height=6),
                    ft.Row([
                        ft.Text(f"{b['check_in']} → {b['check_out']}", size=13),
                        ft.Text(f"{b['guests_count']} гостей", size=13),
                    ], spacing=16),
                    ft.Row([
                        ft.Text(f"₴{b['total_price']:.0f}", size=14, weight=ft.FontWeight.W_600, color=ACCENT),
                        ft.Icon(pay_icon, color=pay_color, size=16),
                        ft.Text(b["payment_status"], size=12, color=pay_color),
                    ], spacing=6),
                    ft.Text(f"ID: {bid}", size=10,color=TEXT_MUTED),
                    ft.Row([
                        ft.OutlinedButton("Скасувати", icon=ft.Icons.CANCEL, style=ft.ButtonStyle(color=DANGER), on_click=make_cancel(bid), visible=can_cancel,
                        ),
                    ], alignment=ft.MainAxisAlignment.END),
                ], spacing=6),
                padding=16, border_radius=12, bgcolor=SURFACE,
                shadow=ft.BoxShadow(blur_radius=6, color=ft.Colors.with_opacity( 0.07, ft.Colors.BLACK)),
            )
            col.controls.append(card)

    async def go_back(e):
        await page.push_route("/home")

    async def logout(e):
        page.session.store.clear()
        await page.push_route("/login")

    return ft.View(
        route="/my_bookings",
        appbar=ft.AppBar(
            leading=ft.IconButton(ft.Icons.ARROW_BACK, icon_color=ft.Colors.WHITE, on_click=go_back),
            title=ft.Text("Мої бронювання", color=TEXT),
            bgcolor=SURFACE,
            actions=[ft.IconButton(ft.Icons.LOGOUT, icon_color=ft.Colors.WHITE, tooltip="Вийти", on_click=logout)],
        ),
        bgcolor=BG,
        scroll=ft.ScrollMode.ADAPTIVE,
        controls=[ft.Container(content=col, padding=16)],
    )
