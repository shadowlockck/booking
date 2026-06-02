
import sys
import os

_SRC = os.path.dirname(os.path.abspath(__file__))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
ASSETS_DIR = os.path.join(_SRC, "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)
import flet as ft

from models.models  import ROLE_ADMIN, ROLE_OWNER, ROLE_GUEST
from views.auth_view   import login_view, register_view
from views.guest_view  import guest_home_view, my_bookings_view
from views.owner_view  import owner_home_view, owner_bookings_view
from views.admin_view  import admin_home_view


async def main(page: ft.Page):
    page.title         = "Онлайн-бронювання"
    page.window.width  = 1100
    page.window.height = 760
    page.window.min_width  = 800
    page.window.min_height = 600
    page.theme_mode    = ft.ThemeMode.DARK
    page.theme         = ft.Theme(color_scheme_seed=ft.Colors.DEEP_PURPLE)
    page.dark_theme    = ft.Theme(color_scheme_seed=ft.Colors.DEEP_PURPLE)
    page.padding       = 0

    async def route_change(e: ft.RouteChangeEvent | str):
        route = e.route if hasattr(e, "route") else str(e)
        page.views.clear()

        is_auth = page.session.store.get("authenticated")
        role    = page.session.store.get("role")

        if route == "/register":
            page.views.append(register_view(page))
            page.update()
            return

        if not is_auth and route not in ("/login", "/register"):
            page.views.append(login_view(page))
            page.update()
            return

        if route == "/login":
            page.views.append(login_view(page))

        elif route == "/home":
            if role == ROLE_ADMIN:
                page.views.append(admin_home_view(page))
            elif role == ROLE_OWNER:
                page.views.append(owner_home_view(page))
            else:
                page.views.append(guest_home_view(page))

        elif route == "/my_bookings":
            if role == ROLE_GUEST:
                page.views.append(guest_home_view(page))
                page.views.append(my_bookings_view(page))
            else:
                page.views.append(login_view(page))

        elif route == "/owner_bookings":
            if role == ROLE_OWNER:
                page.views.append(owner_home_view(page))
                page.views.append(owner_bookings_view(page))
            else:
                page.views.append(login_view(page))

        else:
            page.views.append(login_view(page))

        page.update()

    async def view_pop(e: ft.ViewPopEvent):
        if len(page.views) > 1:
            page.views.pop()
            top = page.views[-1]
            await page.push_route(top.route)

    page.on_route_change = route_change
    page.on_view_pop     = view_pop

    start = page.route if page.route else "/login"
    await route_change(start)


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.FLET_APP, assets_dir=ASSETS_DIR)
