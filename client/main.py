import flet as ft
import httpx
import os

# Dirección de tu servidor (usá tu IP real)
SERVER_URL = "http://192.168.20.229:8000"

async def main(page: ft.Page):
    page.title = "🎨 PokéDraw"
    page.theme_mode = "light"
    page.padding = 20
    page.horizontal_alignment = "center"
    page.bgcolor = "#E8EAF6"
    page.scroll = "auto"

    # 1. Definimos el FilePicker (esto reemplaza a tkinter)
    picker = ft.FilePicker()
    page.overlay.append(picker)
    
    selected_file = None

    # 2. Qué pasa cuando elegimos una foto
    def on_file_picked(e: ft.FilePickerResultEvent):
        nonlocal selected_file
        if e.files:
            selected_file = e.files[0]
            img_preview.src = selected_file.path
            img_preview.visible = True
            status.value = "✅ Imagen lista. ¡Enviá!"
            status.color = "#2E7D32"
            send_btn.disabled = False
        else:
            status.value = "⚠️ Cancelado."
            status.color = "#E65100"
        page.update()

    # Conectar el picker con la función
    picker.on_result = on_file_picked

    # Elementos visuales
    img_preview = ft.Image(src=None, width=200, height=200, fit="contain", visible=False)
    status = ft.Text("👉 Seleccioná un dibujo para empezar", color="#5C6BC0", size=14, italic=True)
    result_text = ft.Text("", weight="bold", size=18, color="#1A237E")

    # 3. Botón para elegir foto (funciona en celular y PC)
    def pick_image(e):
        picker.pick_files(allowed_extensions=["jpg", "jpeg", "png"])

    # 4. Botón para enviar al servidor
    async def send_to_server(e):
        if not selected_file:
            status.value = "❌ Elegí una imagen primero."
            status.color = "#C62828"
            page.update()
            return

        send_btn.disabled = True
        send_btn.text = "⏳ Procesando..."
        status.value = "📡 Conectando con IA..."
        page.update()

        try:
            # Leer el archivo desde el celular/PC
            file_path = selected_file.path
            
            async with httpx.AsyncClient() as client:
                with open(file_path, "rb") as f:
                    resp = await client.post(
                        f"{SERVER_URL}/upload",
                        files={"file": ("drawing.jpg", f, "image/jpeg")},
                        timeout=30.0
                    )
                
                data = resp.json()
                result_text.value = f"✨ ¡{data['pokemon'].upper()}!\n❤️ HP: {data['hp']} | ⚔️ ATK: {data['attack']}"
                status.value = "✅ ¡Carta guardada en el mazo!"
                status.color = "#2E7D32"
                
        except Exception as ex:
            status.value = f"❌ Error: {str(ex)[:30]}"
            status.color = "#C62828"
        finally:
            send_btn.disabled = False
            send_btn.text = "📤 Enviar al servidor"
        page.update()

    # 5. Botón para ver mazo
    async def show_deck(e):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{SERVER_URL}/deck", timeout=10.0)
            cards = resp.json().get("cards", [])
            
            msg = f"🃏 Tenés {len(cards)} cartas en tu mazo."
            if cards:
                last = cards[-1]
                msg += f"\nÚltima: {last['pokemon'].upper()}"
            
            ft.AlertDialog(title=ft.Text("Tu Mazo"), content=ft.Text(msg), actions=[ft.TextButton("Cerrar", on_click=lambda _: page.close_dialog())])
            page.open(ft.AlertDialog(title=ft.Text("Tu Mazo"), content=ft.Text(msg), actions=[ft.TextButton("Cerrar", on_click=lambda _: page.close_dialog())]))
            
        except Exception as ex:
            status.value = f"❌ Error mazo: {str(ex)[:20]}"
        page.update()

    # Botones
    btn_pick = ft.Button("📁 Seleccionar Imagen", on_click=pick_image, bgcolor="#3949AB", color="#FFFFFF", width=300)
    send_btn = ft.Button("📤 Enviar", disabled=True, on_click=send_to_server, bgcolor="#43A047", color="#FFFFFF", width=300)
    btn_deck = ft.Button("🃏 Ver Mazo", on_click=show_deck, bgcolor="#6A1B9A", color="#FFFFFF", width=300)

    # Diseño
    page.add(
        ft.Text(" PokéDraw", size=30, weight="bold", color="#1A237E"),
        ft.Divider(),
        btn_pick,
        img_preview,
        send_btn,
        status,
        result_text,
        ft.Divider(),
        btn_deck
    )

if __name__ == "__main__":
    ft.run(main)