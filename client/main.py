import flet as ft
import httpx


async def main(page: ft.Page):
    page.title = "PokeDraw"
    page.theme_mode = "light"
    page.padding = 10
    page.horizontal_alignment = "center"
    page.bgcolor = "#E8EAF6"
    page.scroll = "auto"

    selected_file_path = {"path": None}

    url_field = ft.TextField(
        label="IP del servidor",
        value="192.168.68.106",
        hint_text="Ej: 192.168.1.100",
        width=300,
        text_size=14,
    )

    status = ft.Text(
        "Selecciona un dibujo para empezar",
        color="#5C6BC0",
        size=14,
        italic=True,
    )

    img_preview = ft.Image(
        src="https://via.placeholder.com/1",
        width=200,
        height=200,
        fit="contain",
        visible=False,
    )

    result_column = ft.Column(visible=False, horizontal_alignment="center")

    async def pick_image(e):
        files = await ft.FilePicker().pick_files(
            allowed_extensions=["jpg", "jpeg", "png", "webp"],
        )
        if files:
            selected_file_path["path"] = files[0].path
            img_preview.src = files[0].path
            img_preview.visible = True
            status.value = "Imagen lista. Toca Enviar!"
            status.color = "#2E7D32"
            send_btn.disabled = False
        else:
            status.value = "Seleccion cancelada."
            status.color = "#E65100"
        page.update()

    async def send_to_server(e):
        file_path = selected_file_path.get("path")
        if not file_path:
            status.value = "Primero elegi una imagen."
            status.color = "#C62828"
            page.update()
            return

        ip = url_field.value.strip()
        base_url = f"http://{ip}:8000"

        send_btn.disabled = True
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

            result_column.controls = [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                pokemon_name.upper(),
                                size=28,
                                weight="bold",
                                color="#1A237E",
                            ),
                            ft.Container(
                                content=ft.Text(
                                    rarity_label,
                                    size=14,
                                    weight="bold",
                                    color="white",
                                ),
                                bgcolor=rarity_color,
                                padding=ft.padding.symmetric(
                                    horizontal=12, vertical=4
                                ),
                                border_radius=12,
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
                                                weight="bold",
                                                color="#C62828",
                                            ),
                                        ],
                                        horizontal_alignment="center",
                                    ),
                                    ft.Column(
                                        [
                                            ft.Text("ATK", size=12, color="#757575"),
                                            ft.Text(
                                                str(attack),
                                                size=24,
                                                weight="bold",
                                                color="#E65100",
                                            ),
                                        ],
                                        horizontal_alignment="center",
                                    ),
                                    ft.Column(
                                        [
                                            ft.Text(
                                                "Similitud", size=12, color="#757575"
                                            ),
                                            ft.Text(
                                                f"{similarity * 100:.1f}%",
                                                size=24,
                                                weight="bold",
                                                color="#1565C0",
                                            ),
                                        ],
                                        horizontal_alignment="center",
                                    ),
                                ],
                                alignment="spaceEvenly",
                            ),
                        ],
                        horizontal_alignment="center",
                        spacing=8,
                    ),
                    padding=20,
                    bgcolor="white",
                    border_radius=16,
                    border=ft.border.all(2, rarity_color),
                    width=320,
                )
            ]
            result_column.visible = True
            status.value = "Carta creada!"
            status.color = "#2E7D32"

        except Exception as ex:
            error_msg = str(ex)[:60]
            status.value = f"Error: {error_msg}"
            status.color = "#C62828"
            result_column.visible = False
        finally:
            send_btn.disabled = False
        page.update()

    async def show_deck(e):
        ip = url_field.value.strip()
        base_url = f"http://{ip}:8000"

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{base_url}/deck", timeout=10.0)
            cards = resp.json().get("cards", [])

            card_texts = []
            for c in cards[-10:]:
                name = c.get("pokemon", "???")
                hp_val = c.get("hp", 0)
                atk_val = c.get("attack", 0)
                sim_val = c.get("similarity", 0)
                card_texts.append(
                    ft.Text(
                        f"{name.upper()} - HP:{hp_val} ATK:{atk_val} ({sim_val*100:.0f}%)",
                        size=13,
                    )
                )

            if not card_texts:
                card_texts.append(ft.Text("No hay cartas todavia.", italic=True))

            dlg = ft.AlertDialog(
                title=ft.Text(f"Tu Mazo ({len(cards)} cartas)"),
                content=ft.Column(
                    card_texts, tight=True, scroll="auto", height=300
                ),
                actions=[
                    ft.TextButton("Cerrar", on_click=lambda _: page.close(dlg)),
                ],
            )
            page.open(dlg)

        except Exception as ex:
            status.value = f"Error mazo: {str(ex)[:30]}"
            status.color = "#C62828"
        page.update()

    btn_pick = ft.Button(
        content="Seleccionar Imagen",
        icon=ft.Icons.IMAGE,
        on_click=pick_image,
        style=ft.ButtonStyle(bgcolor="#3949AB", color="white"),
        width=300,
        height=48,
    )

    send_btn = ft.Button(
        content="Enviar al servidor",
        icon=ft.Icons.SEND,
        disabled=True,
        on_click=send_to_server,
        style=ft.ButtonStyle(bgcolor="#43A047", color="white"),
        width=300,
        height=48,
    )

    btn_deck = ft.Button(
        content="Ver Mazo",
        icon=ft.Icons.COLLECTIONS,
        on_click=show_deck,
        style=ft.ButtonStyle(bgcolor="#6A1B9A", color="white"),
        width=300,
        height=48,
    )

    page.add(
        ft.Container(height=10),
        ft.Text("PokeDraw", size=32, weight="bold", color="#1A237E"),
        ft.Text("Dibuja un Pokemon y descubri cual es!", size=14, color="#5C6BC0"),
        ft.Divider(height=20),
        url_field,
        ft.Container(height=10),
        btn_pick,
        img_preview,
        send_btn,
        ft.Container(height=5),
        status,
        ft.Container(height=10),
        result_column,
        ft.Divider(height=20),
        btn_deck,
        ft.Container(height=20),
    )


if __name__ == "__main__":
    ft.run(main)
