import sys, os, shutil, uuid
_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import flet as ft
from models.models import (
    load_listings, save_listings,
    load_bookings, save_bookings, update_booking_status,
    generate_id, ROLE_OWNER,
)


AMENITIES_LIST = ["Wi-Fi", "Кухня", "Пральна машина", "Кондиціонер",
                  "Парковка", "Балкон", "Телевізор", "Посудомийка"]
PHOTO_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
PHOTOS_DIR = os.path.join(_SRC, "assets", "uploads", "listings")
PHOTO_URL_PREFIX = "/uploads/listings"
os.makedirs(PHOTOS_DIR, exist_ok=True)

_FIELD = {"border_radius": 10, "filled": True}

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


def _tf(**kw):
    return ft.TextField(**_FIELD, **kw)


def _listing_photo_control(lst: dict, size=72) -> ft.Container:
    photos = lst.get("photos", [])
    if photos:
        return ft.Container(
            content=ft.Image(src=photos[0], width=size, height=size, fit=ft.BoxFit.COVER),
            width=size,
            height=size,
            border_radius=8,
            bgcolor=SURFACE2,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )
    return ft.Container(
        content=ft.Icon(ft.Icons.APARTMENT, color=ft.Colors.TEAL_700, size=28),
        width=size,
        height=size,
        border_radius=8,
        bgcolor=SURFACE2,
    )


def _save_listing_photo(listing_id: str, picked_file) -> str:
    original_name = getattr(picked_file, "name", "") or "photo"
    ext = os.path.splitext(original_name)[1].lower()
    if ext.lstrip(".") not in PHOTO_EXTENSIONS:
        ext = ".jpg"

    target_dir = os.path.join(PHOTOS_DIR, listing_id)
    os.makedirs(target_dir, exist_ok=True)
    file_name = f"{uuid.uuid4().hex}{ext}"
    target_path = os.path.join(target_dir, file_name)

    file_bytes = getattr(picked_file, "bytes", None)
    if file_bytes is not None:
        with open(target_path, "wb") as out:
            out.write(file_bytes)
    else:
        source_path = getattr(picked_file, "path", None)
        if not source_path:
            raise ValueError("файл не містить даних для збереження")
        shutil.copy2(source_path, target_path)

    return f"{PHOTO_URL_PREFIX}/{listing_id}/{file_name}"



def owner_home_view(page: ft.Page) -> ft.View:
    user = page.session.store.get("current_user")
    listings = load_listings()
    listings_col = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, expand=True, spacing=8)

    def refresh_list():
        fresh = load_listings()
        listings_col.controls.clear()
        my = [(lid, lst) for lid, lst in fresh.items()
              if lst["owner"] == user]
        if not my:
            listings_col.controls.append(
                ft.Container(
                    ft.Column([
                        ft.Icon(ft.Icons.HOME_WORK, size=64, color=TEXT_MUTED),
                        ft.Text("У вас ще немає оголошень", size=16, color=TEXT_MUTED),
                        ft.Text("Натисніть «Додати оголошення»", size=13, color=TEXT_MUTED),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=40,
                )
            )
        else:
            for lid, lst in my:
                listings_col.controls.append(_listing_row(lst, lid, refresh_list, page))
        page.update()

    def open_add_dialog(e):
        _open_listing_dialog(page, None, None, refresh_list)

    async def go_owner_bookings(e):
        await page.push_route("/owner_bookings")

    async def logout(e):
        page.session.store.clear()
        await page.push_route("/login")

    refresh_list()

    return ft.View(
        route="/home",
        appbar=ft.AppBar(
            leading=ft.Icon(ft.Icons.HOME_WORK, color=ft.Colors.WHITE),
            title=ft.Text("Мої оголошення", color=TEXT),
            bgcolor=ft.Colors.TEAL_700,
            actions=[
                ft.TextButton("Бронювання", style=ft.ButtonStyle(color=ft.Colors.WHITE), on_click=go_owner_bookings),
                ft.IconButton(ft.Icons.LOGOUT, icon_color=ft.Colors.WHITE, tooltip="Вийти", on_click=logout),
            ],
        ),
        bgcolor=BG,
        scroll=ft.ScrollMode.ADAPTIVE,
        controls=[
            ft.Container(
                content=ft.Column([
                    ft.FilledButton("Додати оголошення", icon=ft.Icons.ADD_HOME, on_click=open_add_dialog),
                    listings_col,
                ],spacing=12),
                padding=16,
            )
        ],
    )


def _listing_row(lst: dict, lid: str, refresh, page: ft.Page) -> ft.Container:
    active_badge = ft.Container(
        content=ft.Text("Активне" if lst["is_active"] else "Неактивне", size=11, color=ft.Colors.WHITE),
        bgcolor=ft.Colors.GREEN_600 if lst["is_active"] else ft.Colors.RED_400,
        border_radius=8, padding=ft.Padding.symmetric(horizontal=8, vertical=2),
    )

    def toggle_active(e):
        fresh = load_listings()
        fresh[lid]["is_active"] = not fresh[lid]["is_active"]
        save_listings(fresh)
        refresh()

    def edit_listing(e):
        _open_listing_dialog(page, lst, lid, refresh)

    def delete_listing(e):
        def confirm_delete(ev):
            fresh = load_listings()
            del fresh[lid]
            save_listings(fresh)
            dlg.open = False
            page.update()
            refresh()

        def close_dlg(ev):
            dlg.open = False
            page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Видалити оголошення?"),
            content=ft.Text(f'«{lst["title"]}» буде видалено назавжди.'),
            actions=[
                ft.TextButton("Скасувати", on_click=close_dlg),
                ft.FilledButton("Видалити", style=ft.ButtonStyle(bgcolor=ft.Colors.RED_400), on_click=confirm_delete),
            ],
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    return ft.Container(
        content=ft.Column([
            ft.Row([
                _listing_photo_control(lst),
                ft.Text(lst["title"], size=15, weight=ft.FontWeight.BOLD, expand=True),
                active_badge,
            ]),
            ft.Text(f"{lst['city']} · {lst['address']}", size=12, color=TEXT_MUTED),
            ft.Row([
                ft.Text(f"₴{lst['price_per_night']:.0f}/ніч", size=13, color=ft.Colors.TEAL_700, weight=ft.FontWeight.W_600),
                ft.Text(f"· {lst['property_type']}", size=12),
                ft.Text(f"· до {lst['max_guests']} гостей", size=12),
            ], spacing=6),
            ft.Row([
                ft.IconButton(ft.Icons.EDIT, icon_color=ft.Colors.TEAL_700, tooltip="Редагувати", on_click=edit_listing),
                ft.IconButton(ft.Icons.TOGGLE_ON if lst["is_active"] else ft.Icons.TOGGLE_OFF, icon_color=ft.Colors.GREEN_600 if lst["is_active"] else ft.Colors.RED_400,tooltip="Активувати/Деактивувати", on_click=toggle_active),
                ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, tooltip="Видалити", on_click=delete_listing),
            ], alignment=ft.MainAxisAlignment.END),
        ],
        spacing=6),
        padding=16,
        border_radius=12,
        bgcolor=SURFACE,
        shadow=ft.BoxShadow(blur_radius=6, color=ft.Colors.with_opacity(0.07, ft.Colors.BLACK)),
    )


def _open_listing_dialog(page, lst, lid, refresh):
    is_edit = lid is not None
    user = page.session.store.get("current_user")
    listing_id = lid if is_edit else generate_id("LST")
    photos = list(lst.get("photos", [])) if is_edit else []

    title_f = ft.TextField(label="Назва", value=lst["title"] if is_edit else "", **_FIELD, width=340)
    city_f = ft.TextField(label="Місто", value=lst["city"] if is_edit else "", **_FIELD, width=160)
    addr_f = ft.TextField(label="Адреса", value=lst["address"] if is_edit else "", **_FIELD, width=340)
    price_f = ft.TextField(label="Ціна/ніч (₴)", value=str(lst["price_per_night"]) if is_edit else "", **_FIELD, width=130)
    guests_f = ft.TextField(label="Макс. гостей", value=str(lst["max_guests"]) if is_edit else "2", **_FIELD, width=120)
    rooms_f = ft.TextField(label="Кімнат", value=str(lst["rooms"]) if is_edit else "1", **_FIELD, width=100)
    desc_f = ft.TextField(label="Опис", multiline=True, min_lines=3, value=lst.get("description", "") if is_edit else "", **_FIELD, width=340)

    type_dd = ft.Dropdown(
        label="Тип помешкання",
        options=[ft.DropdownOption(t) for t in ["Квартира", "Будинок", "Кімната"]],
        value=lst["property_type"] if is_edit else "Квартира",
        width=160, border_radius=10,
    )

    existing_am = lst.get("amenities", []) if is_edit else []
    am_checks = [
        ft.Checkbox(label=a, value=(a in existing_am))
        for a in AMENITIES_LIST
    ]

    err_txt = ft.Text(color=ft.Colors.RED_400, size=12)
    photos_row = ft.Row(wrap=True, spacing=8, run_spacing=8)

    def make_remove_photo(src):
        def remove_photo(ev):
            if src in photos:
                photos.remove(src)
            refresh_photos()
            page.update()
        return remove_photo

    def refresh_photos():
        photos_row.controls.clear()
        if not photos:
            photos_row.controls.append(ft.Text("Фото ще не додано", size=12, color=TEXT_MUTED))
            return

        for src in photos:
            photos_row.controls.append(
                ft.Container(
                    content=ft.Column([
                        _listing_photo_control({"photos": [src]}, size=84),
                        ft.IconButton(
                            ft.Icons.DELETE_OUTLINE,
                            icon_color=DANGER,
                            icon_size=16,
                            width=32,
                            height=28,
                            tooltip="Прибрати фото",
                            on_click=make_remove_photo(src),
                        ),
                    ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    width=96,
                    padding=4,
                    border_radius=8,
                    bgcolor=SURFACE2,
                )
            )

    async def pick_photos(ev):
        files = await ft.FilePicker().pick_files(
            dialog_title="Оберіть фото помешкання",
            allow_multiple=True,
            with_data=True,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=sorted(PHOTO_EXTENSIONS),
        )
        if not files:
            return

        try:
            for picked_file in files:
                photos.append(_save_listing_photo(listing_id, picked_file))
            err_txt.value = ""
        except Exception as ex:
            err_txt.value = f"Не вдалося додати фото: {ex}"
        refresh_photos()
        page.update()

    refresh_photos()

    def save(ev):
        try:
            price  = float(price_f.value)
            guests = int(guests_f.value)
            rooms  = int(rooms_f.value)
        except ValueError:
            err_txt.value = "Перевірте числові поля"
            page.update()
            return


        if not title_f.value.strip() or not city_f.value.strip():
            err_txt.value = "Назва та місто обов'язкові"
            page.update()
            return



        am = [cb.label for cb in am_checks if cb.value]
        fresh = load_listings()
        new_lid = listing_id
        fresh[new_lid] = {
            "id":              new_lid,
            "owner":           user,
            "title":           title_f.value.strip(),
            "city":            city_f.value.strip(),
            "address":         addr_f.value.strip(),
            "property_type":   type_dd.value,
            "price_per_night": price,
            "max_guests":      guests,
            "rooms":           rooms,
            "description":     desc_f.value.strip(),
            "amenities":       am,
            "photos":          list(photos),
            "is_active":       lst.get("is_active", True) if is_edit else True,
        }
        save_listings(fresh)
        dlg.open = False
        page.update()
        refresh()

    def close(ev):
        dlg.open = False
        page.update()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Редагувати" if is_edit else "Нове оголошення"),
        content=ft.Column([
            title_f,
            ft.Row([city_f, type_dd], spacing=10),
            addr_f,
            ft.Row([price_f, guests_f, rooms_f], spacing=10),
            desc_f,
            ft.Text("Фото об'єкта:", size=13),
            ft.Row([
                ft.OutlinedButton("Додати фото", icon=ft.Icons.UPLOAD_FILE, on_click=pick_photos),
            ]),
            photos_row,
            ft.Text("Зручності:", size=13),
            ft.Row(am_checks, wrap=True, spacing=4),
            err_txt,
        ],spacing=10, width=380, scroll=ft.ScrollMode.ADAPTIVE),
        actions=[
            ft.TextButton("Скасувати", on_click=close),
            ft.FilledButton("Зберегти", icon=ft.Icons.SAVE, on_click=save),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(dlg)
    dlg.open = True
    page.update()


def owner_bookings_view(page: ft.Page) -> ft.View:
    user     = page.session.store.get("current_user")
    bookings = load_bookings()
    listings = load_listings()

    my_listings = {lid for lid, lst in listings.items() if lst["owner"] == user}

    col = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, expand=True, spacing=8)

    status_colors = {
        "confirmed": ft.Colors.GREEN_600,
        "pending":   ft.Colors.ORANGE_600,
        "cancelled": ft.Colors.RED_400,
        "completed": ft.Colors.GREY_500,
    }

    my_bkgs = [(bid, b) for bid, b in bookings.items()
               if b["listing_id"] in my_listings]

    if not my_bkgs:
        col.controls.append(
            ft.Container(
                ft.Column([
                    ft.Icon(ft.Icons.CALENDAR_TODAY, size=64, color=TEXT_MUTED),
                    ft.Text("Ще немає бронювань ваших помешкань", size=15, color=TEXT_MUTED),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=40,
            )
        )
    else:
        for bid, b in sorted(my_bkgs, key=lambda x: x[1]["created_at"], reverse=True):
            lst = listings.get(b["listing_id"], {})

            def make_confirm(bk_id):
                def do_confirm(ev):
                    update_booking_status(bk_id, "completed")
                    page.go("/owner_bookings")
                return do_confirm

            card = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(lst.get("title", "—"), size=15, weight=ft.FontWeight.BOLD, expand=True),
                        ft.Text(b["status"].upper(), size=11, color=status_colors.get(b["status"], ft.Colors.TEAL_700), weight=ft.FontWeight.BOLD),
                    ]),
                    ft.Text(f"Гість: {b['guest_username']}", size=13),
                    ft.Row([
                        ft.Text(f"{b['check_in']} → {b['check_out']}", size=13),
                        ft.Text(f"{b['guests_count']} гостей", size=13),
                    ], spacing=12),
                    ft.Text(f"₴{b['total_price']:.0f} · оплата: {b['payment_status']}", size=13, color=ft.Colors.TEAL_700),
                    ft.Row([
                        ft.OutlinedButton("Завершити", icon=ft.Icons.DONE_ALL, on_click=make_confirm(bid), visible=(b["status"] == "confirmed"),
                        )
                    ], alignment=ft.MainAxisAlignment.END),
                ], spacing=6),
                padding=16, border_radius=12, bgcolor=SURFACE,
                shadow=ft.BoxShadow(blur_radius=6, color=ft.Colors.with_opacity(0.07, ft.Colors.BLACK)),
            )
            col.controls.append(card)

    async def go_back(e):
        await page.push_route("/home")

    async def logout(e):
        page.session.store.clear()
        await page.push_route("/login")

    return ft.View(
        route="/owner_bookings",
        appbar=ft.AppBar(
            leading=ft.IconButton(ft.Icons.ARROW_BACK, icon_color=ft.Colors.WHITE, on_click=go_back),
            title=ft.Text("Бронювання моїх помешкань", color=ft.Colors.WHITE),
            bgcolor=ft.Colors.TEAL_700,
            actions=[ft.IconButton(ft.Icons.LOGOUT, icon_color=ft.Colors.WHITE, tooltip="Вийти", on_click=logout)],
        ),
        bgcolor=BG,
        scroll=ft.ScrollMode.ADAPTIVE,
        controls=[ft.Container(content=col, padding=16)],
    )
