import threading
import time
from datetime import datetime
import pandas as pd
import telebot
from telebot import types
import yfinance as yf

# Tus credenciales directas
TOKEN = "8812503803:AAGhDdtvMmC_P_pnvhWLTIQ-VCr6JTg_KcA"
CHAT_ID = "5574325279"

bot = telebot.TeleBot(TOKEN)


def obtener_analisis():
  try:
    # 1. Obtener datos diarios (1D) para los niveles clave (Alto, Bajo, 50%)
    data_1d = yf.download(
        tickers="EURUSD=X", period="5d", interval="1d", progress=False
    )
    if data_1d.empty:
      return "No se pudieron obtener datos diarios del EUR/USD."

    if isinstance(data_1d.columns, pd.MultiIndex):
      data_1d.columns = data_1d.columns.get_level_values(0)

    # Tomamos la vela anterior completada del día
    vela_anterior = data_1d.iloc[-2]
    alto_1d = float(vela_anterior["High"])
    bajo_1d = float(vela_anterior["Low"])
    mid_50 = (alto_1d + bajo_1d) / 2

    # 2. Obtener precio actual (intradía)
    data_intraday = yf.download(
        tickers="EURUSD=X", period="1d", interval="15m", progress=False
    )
    if isinstance(data_intraday.columns, pd.MultiIndex):
      data_intraday.columns = data_intraday.columns.get_level_values(0)

    precio_actual = float(data_intraday["Close"].iloc[-1])

    # 3. Lógica basada en la estrategia de rangos y barrido de liquidez
    # Margen de tolerancia para detectar acercamiento a los extremos (1.5%)
    margen = (alto_1d - bajo_1d) * 0.015

    estado = "ZONA_MEDIA"
    if precio_actual >= (alto_1d - margen):
      estado = "VENTA_EXTREMO"  # Tocó el Alto -> Venta hacia el 50%
    elif precio_actual <= (bajo_1d + margen):
      estado = "COMPRA_EXTREMO"  # Tocó el Bajo -> Compra hacia el 50%

    # Construcción del reporte para Telegram
    mensaje = f"📊 *ESTRATEGIA RANGOS DIARIOS (EUR/USD)*\n"
    mensaje += f"💵 *Precio Actual:* `{precio_actual:.5f}`\n\n"
    mensaje += f"📈 *Alto Día Anterior:* `{alto_1d:.5f}`\n"
    mensaje += f"🎯 *Nivel 50% (Equilibrio):* `{mid_50:.5f}`\n"
    mensaje += f"📉 *Bajo Día Anterior:* `{bajo_1d:.5f}`\n"
    mensaje += f"⏱ *Hora:* `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n\n"

    if estado == "VENTA_EXTREMO":
      mensaje += "🔴 🔻 **ACCIÓN EXACTA: VENDER (SELL)** 🔻\n"
      mensaje += (
          "👉 *Qué hacer:* El precio llegó al **Máximo (Alto)** del día anterior"
          " y muestra rechazo.\n"
          f"🎯 *Objetivo:* Apunta hacia el nivel del **50% (`{mid_50:.5f}`)** o"
          " el Bajo.\n"
          "🛑 *Stop Loss:* Unos pips por encima del máximo diario."
      )
    elif estado == "COMPRA_EXTREMO":
      mensaje += "🟢 🚀 **ACCIÓN EXACTA: COMPRAR (BUY)** 🚀\n"
      mensaje += (
          "👉 *Qué hacer:* El precio barrió el **Mínimo (Bajo)** del día anterior"
          " y rebotó.\n"
          f"🎯 *Objetivo:* Apunta hacia el nivel del **50% (`{mid_50:.5f}`)** o"
          " el Alto.\n"
          "🛑 *Stop Loss:* Unos pips por debajo del mínimo diario."
      )
    else:
      mensaje += "⚪ ⏳ **ACCIÓN EXACTA: EVITAR OPERAR (ZONA MEDIA)** ⏳\n"
      mensaje += (
          "👉 *Qué hacer:* El precio está flotando en la zona del **50%** sin"
          " tocar ningún extremo.\n"
          "🛡 *Protección:* No hay ventaja clara. Evita operar hasta que llegue"
          " a los límites."
      )

    return mensaje
  except Exception as e:
    return f"⚠️ Error al calcular los niveles de la estrategia: {e}"


# Crear botones interactivos del menú
def crear_menu():
  markup = types.InlineKeyboardMarkup(row_width=2)
  btn_analisis = types.InlineKeyboardButton(
      "📊 Solicitar Análisis y Orden", callback_data="solicitar_analisis"
  )
  btn_plan = types.InlineKeyboardButton(
      "📋 Reglas de Gestión", callback_data="que_hacer"
  )
  markup.add(btn_analisis, btn_plan)
  return markup


@bot.message_handler(commands=["start", "menu"])
def enviar_menu(message):
  texto = (
      "🤖 *Panel de Trading EUR/USD Activo*\nUsa los botones de abajo para"
      " pedir tu orden basada en los rangos diarios:"
  )
  bot.send_message(
      message.chat.id, texto, reply_markup=crear_menu(), parse_mode="Markdown"
  )


@bot.callback_query_handler(func=lambda call: True)
def manejar_botones(call):
  if call.data == "solicitar_analisis":
    bot.answer_callback_query(call.id, "Calculando niveles diarios...")
    resultado = obtener_analisis()
    bot.send_message(
        call.message.chat.id,
        resultado,
        reply_markup=crear_menu(),
        parse_mode="Markdown",
    )
  elif call.data == "que_hacer":
    bot.answer_callback_query(call.id, "Cargando reglas...")
    guia = (
        "📋 *REGLAS DE LOS RANGOS DIARIOS*\n\n1️⃣ **Extremos:** Solo operamos"
        " cuando el precio toca o barre el Alto o el Bajo del día anterior.\n2️⃣"
        " **Objetivo:** El 50% es la primera parada lógica de beneficio.\n3️⃣"
        " **Paciencia:** Si está en la zona media, se descarta para proteger"
        " el capital."
    )
    bot.send_message(
        call.message.chat.id,
        guia,
        reply_markup=crear_menu(),
        parse_mode="Markdown",
    )


# Bucle automático cada 1 hora para enviar notificaciones
def bucle_automatico():
  while True:
    time.sleep(3600)  # Espera 1 hora exacta
    try:
      informe = obtener_analisis()
      mensaje_final = (
          "⏰ *INFORME AUTOMÁTICO DE RANGOS (CADA HORA)*\n\n" + informe
      )
      bot.send_message(
          CHAT_ID,
          mensaje_final,
          reply_markup=crear_menu(),
          parse_mode="Markdown",
      )
    except Exception as e:
      print(f"Error en el envío automático: {e}")


if __name__ == "__main__":
  # Arranca el hilo en segundo plano para las alertas automáticas
  hilo_hora = threading.Thread(target=bucle_automatico, daemon=True)
  hilo_hora.start()

  print("Bot sincronizado con estrategia de rangos y listo en la nube...")
  # skip_pending=True evita el error 409 al descartar peticiones viejas atascadas
  bot.infinity_polling(skip_pending=True)
