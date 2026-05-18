import flet as ft
import httpx
import os
import json

# Archivo para guardar la configuracion del servidor
CONFIG_FILE = "pokedraw_config.json"


def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {"server_url": "http://192.168.1.1:8000"}


def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
    except Exception:
        pass


async def main(page: ft.Page):
    page.title = "PokeDraw"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 10
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.bgcolor = "#E8EAF6"
    page.scroll = ft.ScrollMode.AUTO

    config = load_config()
    server_url = config.get("server_url", "http://192.168.1.1:8000")

    selected_file_path = {"path": None}

    # --- Controles de UI ---

    # Campo para la URL del servidor
    url_field = ft.TextField(
        label="IP del servidor (Arduino UNO Q)",
        value=server_url,
        prefix_text="http://",
        suffix_text=":8000",
        hint_text="192.168.1.100",
        width=320,
        text_size=14,
        border_color="#3949AB",
    )

    status = ft.Text(
        "Selecciona un dibujo para empezar",
        color="#5C6BC0",
        size=14,
        italic=True,
        text_align=ft.TextAlign.CENTER,
    )

    img_preview = ft.Image(
        src=None,
        width=200,
        height=200,
        fit=ft.ImageFit.CONTAIN,
        visible=False,
        border_radius=ft.border_radius.all(10),
    )

    result_container = ft.Container(visible=False)

    # --- File Picker ---
    picker = ft.FilePicker()
    page.services.append(picker)

    def on_file_picked(e: ft.FilePickerResultEvent):
        if e.files:
            selected_file_path["path"] = e.files[0].path
            img_preview.src = e.files[0].path
            img_preview.visible = True
            status.value = "Imagen lista. Toca Enviar!"
            status.color = "#2E7D32"
            send_btn.disabled = False
        else:
            status.value = "Seleccion cancelada."
            status.color = "#E65100"
        page.update()

    picker.on_result = on_file_picked

    def pick_image(e):
        picker.pick_files(
            allowed_extensions=["jpg", "jpeg", "png", "webp"],
            dialog_title="Elegir imagen del dibujo",
        )

    # --- Enviar al servidor ---
    async def send_to_server(e):
        file_path = selected_file_path.get("path")
        if not file_path:
            status.value = "Primero elegi una imagen."
            status.color = "#C62828"
            page.update()
            return

        # Construir URL del servidor
        raw_url = url_field.value.strip()
        if raw_url.startswith("http://") or raw_url.startswith("https://"):
            base_url = raw_url.rstrip("/")
        else:
            base_url = f"http://{raw_url}:8000"

        # Guardar config
        save_config({"server_url": raw_url})

        send_btn.disabled = True
        send_btn.text = "Procesando..."
        status.value = "Conectando con la IA..."
        status.color = "#1565C0"
        page.update()

        try:
            async with httpx.AsyncClient() as client:
                with open(file_path, "rb") as f:
                    resp = await client.post(
                        f"{base_url}/upload",
                        files={"file": ("drawing.jpg", f, "image/jpeg")},
                        timeout=60.0,
                    )

                if resp.status_code != 200:
                    raise Exception(f"Error del servidor: {resp.status_code}")

                data = resp.json()

            pokemon_name = data.get("pokemon", "???")
            hp = data.get("hp", 0)
            attack = data.get("attack", 0)
            similarity = data.get("similarity", 0)
            rarity = data.get("rarity", {})
            rarity_label = rarity.get("label", "BASICO")
            rarity_color = rarity.get("color", "#9E9E9E")
            stars = rarity.get("stars", 1)

            star_text = "".join(["*" for _ in range(stars)])

            result_container.content = ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            pokemon_name.upper(),
                            size=28,
                            weight=ft.FontWeight.BOLD,
                            color="#1A237E",
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Container(
                            content=ft.Text(
                                rarity_label,
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color="white",
                                text_align=ft.TextAlign.CENTER,
                            ),
                            bgcolor=rarity_color,
                            padding=ft.padding.symmetric(horizontal=12, vertical=4),
                            border_radius=ft.border_radius.all(12),
                        ),
                        ft.Divider(height=1),
                        ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text("HP", size=12, color="#757575"),
                                        ft.Text(
                                            str(hp),
                                            size=24,
                                            weight=ft.FontWeight.BOLD,
                                            color="#C62828",
                                        ),
                                    ],
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                ft.Column(
                                    [
                                        ft.Text("ATK", size=12, color="#757575"),
                                        ft.Text(
                                            str(attack),
                                            size=24,
                                            weight=ft.FontWeight.BOLD,
                                            color="#E65100",
                                        ),
                                    ],
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                ft.Column(
                                    [
                                        ft.Text("Similitud", size=12, color="#757575"),
                                        ft.Text(
                                            f"{similarity * 100:.1f}%",
                                            size=24,
                                            weight=ft.FontWeight.BOLD,
                                            color="#1565C0",
                                        ),
                                    ],
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
                padding=20,
                bgcolor="white",
                border_radius=ft.border_radius.all(16),
                border=ft.border.all(2, rarity_color),
                width=320,
            )
            result_container.visible = True

            status.value = "Carta creada!"
            status.color = "#2E7D32"

        except httpx.ConnectError:
            status.value = "No se pudo conectar al servidor. Verifica la IP."
            status.color = "#C62828"
            result_container.visible = False
        except httpx.TimeoutException:
            status.value = "Tiempo agotado. El servidor tarda mucho."
            status.color = "#C62828"
            result_container.visible = False
        except Exception as ex:
            error_msg = str(ex)[:50]
            status.value = f"Error: {error_msg}"
            status.color = "#C62828"
            result_container.visible = False
        finally:
            send_btn.disabled = False
            send_btn.text = "Enviar al servidor"
        page.update()

    # --- Ver mazo ---
    async def show_deck(e):
        raw_url = url_field.value.strip()
        if raw_url.startswith("http://") or raw_url.startswith("https://"):
            base_url = raw_url.rstrip("/")
        else:
            base_url = f"http://{raw_url}:8000"

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{base_url}/deck", timeout=10.0)
            cards = resp.json().get("cards", [])

            card_items = []
            for c in cards[-10:]:
                name = c.get("pokemon", "???")
                hp_val = c.get("hp", 0)
                atk_val = c.get("attack", 0)
                sim_val = c.get("similarity", 0)
                card_items.append(
                    ft.Text(
                        f"{name.upper()} - HP:{hp_val} ATK:{atk_val} ({sim_val*100:.0f}%)",
                        size=13,
                    )
                )

            if not card_items:
                card_items.append(ft.Text("No hay cartas todavia.", italic=True))

            dlg = ft.AlertDialog(
                title=ft.Text(f"Tu Mazo ({len(cards)} cartas)"),
                content=ft.Column(card_items, tight=True, scroll=ft.ScrollMode.AUTO, height=300),
                actions=[
                    ft.TextButton("Cerrar", on_click=lambda _: page.close_dialog()),
                ],
            )
            page.open(dlg)

        except Exception as ex:
            status.value = f"Error al cargar mazo: {str(ex)[:30]}"
            status.color = "#C62828"
        page.update()

    # --- Botones ---
    btn_pick = ft.ElevatedButton(
        "Seleccionar Imagen",
        icon=ft.Icons.IMAGE,
        on_click=pick_image,
        bgcolor="#3949AB",
        color="white",
        width=300,
        height=48,
    )

    send_btn = ft.ElevatedButton(
        "Enviar al servidor",
        icon=ft.Icons.SEND,
        disabled=True,
        on_click=send_to_server,
        bgcolor="#43A047",
        color="white",
        width=300,
        height=48,
    )

    btn_deck = ft.ElevatedButton(
        "Ver Mazo",
        icon=ft.Icons.COLLECTIONS,
        on_click=show_deck,
        bgcolor="#6A1B9A",
        color="white",
        width=300,
        height=48,
    )

    # --- Layout ---
    page.add(
        ft.Container(height=10),
        ft.Text(
            "PokeDraw",
            size=32,
            weight=ft.FontWeight.BOLD,
            color="#1A237E",
            text_align=ft.TextAlign.CENTER,
        ),
        ft.Text(
            "Dibuja un Pokemon y descubri cual es!",
            size=14,
            color="#5C6BC0",
            text_align=ft.TextAlign.CENTER,
        ),
        ft.Divider(height=20),
        url_field,
        ft.Container(height=10),
        btn_pick,
        img_preview,
        send_btn,
        ft.Container(height=5),
        status,
        ft.Container(height=10),
        result_container,
        ft.Divider(height=20),
        btn_deck,
        ft.Container(height=20),
    )


if __name__ == "__main__":
    ft.app(main)
