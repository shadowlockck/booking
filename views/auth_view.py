import sys, os, re
_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import flet as ft
from models.models import get_user, add_user, user_exists, verify_password, ROLE_GUEST, ROLE_OWNER

ACCENT      = "#7C3AED"
ACCENT_LIGHT= "#A78BFA"
BG          = "#0F0F1A"
SURFACE     = "#1A1A2E"
BORDER      = "#2D2D4E"
TEXT        = "#E2E8F0"
TEXT_MUTED  = "#94A3B8"
DANGER      = "#EF4444"
SUCCESS     = "#22C55E"
WARNING     = "#F59E0B"

_F = {"border_radius": 10, "filled": True,
      "border_color": BORDER,
      "focused_border_color": ACCENT_LIGHT,
      "cursor_color": ACCENT_LIGHT,
      "label_style": ft.TextStyle(color=TEXT_MUTED),
      "text_style":  ft.TextStyle(color=TEXT),
      "bgcolor": SURFACE}

def _tf(**kw):
    return ft.TextField(**_F, **kw)

def _err(msg=""):
    return ft.Text(msg, color=DANGER, size=12)

def validate_registration(username, password, email, full_name):
    errors = []
    if len(username) < 3:
        errors.append("Логін: мінімум 3 символи")
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        errors.append("Логін: тільки латинські літери, цифри та _")
    if len(password) < 6:
        errors.append("Пароль: мінімум 6 символів")
    if not any(c.isupper() for c in password):
        errors.append("Пароль: має містити хоча б одну велику літеру")
    if not any(c.isdigit() for c in password):
        errors.append("Пароль: має містити хоча б одну цифру")
    if email and not re.match(r"^[\w.\-+]+@[\w\-]+\.[a-z]{2,}$", email, re.I):
        errors.append("Email: невірний формат")
    if full_name and len(full_name) < 2:
        errors.append("Ім'я: мінімум 2 символи")
    return errors

def _wrap(content, route):
    return ft.View(
        route=route,
        bgcolor=BG,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.ADAPTIVE,
        controls=[content],
    )


def login_view(page: ft.Page) -> ft.View:
    err_txt    = ft.Text("", color=DANGER, size=12)
    username_f = _tf(label="Логін", autofocus=True, width=320)
    password_f = _tf(label="Пароль", password=True, can_reveal_password=True, width=320)

    async def do_login(e):
        u = username_f.value.strip()
        p = password_f.value
        user = get_user(u)
        if user and verify_password(p, user["password"]):
            page.session.store.set("authenticated", True)
            page.session.store.set("current_user", u)
            page.session.store.set("role", user["role"])
            await page.push_route("/home")
        else:
            err_txt.value = "Невірний логін або пароль"
            page.update()

    async def go_reg(e):
        await page.push_route("/register")

    card = ft.Container(
        ft.Column([
            ft.Column([
                ft.Container(
                    ft.Icon(ft.Icons.HOTEL, size=36, color="#FFFFFF"),
                    bgcolor=ACCENT, border_radius=16, padding=14,
                ),
                ft.Text("Booking System", size=26, weight=ft.FontWeight.BOLD, color=TEXT),
                ft.Text("Онлайн-бронювання помешкань", size=13, color=TEXT_MUTED),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
            ft.Container(height=8),
            username_f, password_f, err_txt,
            ft.Container(height=4),
            ft.FilledButton(
                "Увійти", width=320, icon=ft.Icons.LOGIN,
                on_click=do_login,
                style=ft.ButtonStyle(
                    bgcolor=ACCENT,
                    color="#FFFFFF",
                    shape=ft.RoundedRectangleBorder(radius=10),
                    padding=ft.Padding.symmetric(vertical=14),
                ),
            ),
            ft.Divider(color=BORDER),
            ft.TextButton(
                "Немає акаунту? Зареєструватися", on_click=go_reg, style=ft.ButtonStyle(color=ACCENT_LIGHT),
            ),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
        padding=36, bgcolor=SURFACE, border_radius=20, width=400,
        border=ft.Border.all(1, BORDER),
        shadow=ft.BoxShadow(blur_radius=40, color=ft.Colors.with_opacity(0.5, ACCENT)),
    )
    return _wrap(card, "/login")


def register_view(page: ft.Page) -> ft.View:
    errors_col = ft.Column(spacing=2)
    username_f = _tf(label="Логін *", autofocus=True, width=320, hint_text="мін. 3 символи, лат. літери")
    password_f = _tf(label="Пароль *", password=True, can_reveal_password=True, width=320, hint_text="мін. 6 символів, велика літера + цифра")
    confirm_f  = _tf(label="Повтор паролю *", password=True, can_reveal_password=True, width=320)
    fullname_f = _tf(label="Повне ім'я", width=320)
    email_f    = _tf(label="Email", width=320)
    phone_f    = _tf(label="Телефон", width=320)

    strength_bar = ft.ProgressBar(
        value=0, width=320, height=4,
        color=DANGER, bgcolor=BORDER,
    )
    strength_lbl = ft.Text("", size=11, color=TEXT_MUTED)

    def on_password_change(e):
        p = password_f.value
        score = sum([
            len(p) >= 6,
            len(p) >= 10,
            any(c.isupper() for c in p),
            any(c.isdigit() for c in p),
            any(c in "!@#$%^&*()-_=+" for c in p),
        ])
        bar_val  = score / 5
        bar_color= [DANGER, DANGER, WARNING, WARNING, SUCCESS][min(score,4)]
        labels   = ["", "Дуже слабкий", "Слабкий", "Середній", "Надійний", "Дуже надійний"]
        strength_bar.value = bar_val
        strength_bar.color = bar_color
        strength_lbl.value = labels[score] if p else ""
        strength_lbl.color = bar_color
        page.update()

    password_f.on_change = on_password_change

    role_group = ft.RadioGroup(
        value=ROLE_GUEST,
        content=ft.Row([
            ft.Radio(value=ROLE_GUEST,  label="Гість",   fill_color=ACCENT_LIGHT),
            ft.Radio(value=ROLE_OWNER,  label="Власник", fill_color=ACCENT_LIGHT),
        ], spacing=24),
    )

    async def do_register(e):
        u  = username_f.value.strip()
        p  = password_f.value
        p2 = confirm_f.value
        fn = fullname_f.value.strip()
        em = email_f.value.strip()
        ph = phone_f.value.strip()
        role = role_group.value

        errs = validate_registration(u, p, em, fn)
        if p != p2:
            errs.append("Паролі не збігаються")
        if user_exists(u):
            errs.append(f"Логін «{u}» вже зайнятий")

        errors_col.controls.clear()
        if errs:
            for msg in errs:
                errors_col.controls.append(
                    ft.Row([
                        ft.Icon(ft.Icons.ERROR_OUTLINE, color=DANGER, size=14),
                        ft.Text(msg, color=DANGER, size=12),
                    ], spacing=4)
                )
        else:
            add_user(u, p, role, fn, em, ph)
            await page.push_route("/login")
            return
        page.update()

    async def go_login(e):
        await page.push_route("/login")

    card = ft.Container(
        ft.Column([
            ft.Row([
                ft.Container(
                    ft.Icon(ft.Icons.PERSON_ADD, size=20, color="#FFFFFF"),
                    bgcolor=ACCENT, border_radius=10, padding=8,
                ),
                ft.Text("Реєстрація", size=20,
                        weight=ft.FontWeight.BOLD, color=TEXT),
            ], spacing=10),
            ft.Divider(color=BORDER),
            username_f, password_f,
            strength_bar, strength_lbl,
            confirm_f,
            fullname_f, email_f, phone_f,
            ft.Text("Оберіть роль:", size=13, color=TEXT_MUTED),
            role_group,
            errors_col,
            ft.FilledButton(
                "Зареєструватися", width=320, icon=ft.Icons.CHECK,
                on_click=do_register,
                style=ft.ButtonStyle(
                    bgcolor=ACCENT, color="#FFFFFF",
                    shape=ft.RoundedRectangleBorder(radius=10),
                    padding=ft.Padding.symmetric(vertical=14),
                ),
            ),
            ft.TextButton(
                "Вже є акаунт? Увійти", on_click=go_login,
                style=ft.ButtonStyle(color=ACCENT_LIGHT),
            ),
        ],

            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10, scroll=ft.ScrollMode.ADAPTIVE),
            padding=36, bgcolor=SURFACE, border_radius=20, width=430,
            border=ft.Border.all(1, BORDER),
            shadow=ft.BoxShadow(blur_radius=40,
            color=ft.Colors.with_opacity(0.5, ACCENT)),
    )
    return _wrap(card, "/register")
