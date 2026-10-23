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
  data = yf.download(
      tickers="EURUSD=X", period="5d", interval="1h", progress=False
  )
  if data.empty:
    return "No se pudieron obtener datos del EUR/USD."

  if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)

  cierre = data["Close"]
  data["SMA_20"] = cierre.rolling(window=20).mean()
  data["SMA_50"] = cierre.rolling(window=50).mean()

  delta = cierre.diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
  rs = gain / loss
  data["RSI"] = 100 - (100 / (1 + rs))

  precio_actual = float(cierre.iloc[-1])
  sma20 = float(data["SMA_20"].iloc[-1])
  sma50 = float(data["SMA_50"].iloc[-1])
  rsi_actual = float(data["RSI"].iloc[-1])

  estado = "NEUTRAL"
  if sma20 > sma50 and rsi_actual < 70:
    estado = "COMPRA"
  elif sma20 < sma50 and rsi_actual > 30:
    estado = "VENTA"

  # Encabezado del reporte
  mensaje = f"📊 *ANÁLISIS TÉCNICO EUR/USD*\n"
  mensaje += f"💵 *Precio Actual:* `{precio_actual:.5f}`\n"
  mensaje += f"📈 *RSI (14):* `{rsi_actual:.2f}`\n"
  mensaje += f"⏱ *Hora:* `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n\n"

  # Instrucción exacta y directa de lo que hay que hacer
  if estado == "COMPRA":
    mensaje += "🟢 🚀 **ACCIÓN EXACTA: COMPRAR (BUY)** 🚀\n"
    mensaje += (
        "👉 *Qué hacer:* El mercado muestra fuerza alcista. Abre una posición de"
        " **COMPRA** ahora o en el siguiente pequeño retroceso.\n"
        "🛑 *Stop Loss:* Colócalo unos pips por debajo del último soporte"
        " reciente.\n"
        "🎯 *Take Profit:* Busca un objetivo con una relación de riesgo/beneficio"
        " favorable (1:2)."
    )
  elif estado == "VENTA":
    mensaje += "🔴 🔻 **ACCIÓN EXACTA: VENDER (SELL)** 🔻\n"
    mensaje += (
        "👉 *Qué hacer:* El mercado muestra tendencia bajista. Abre una posición"
        " de **VENTA** ahora o en el siguiente rebote.\n"
        "🛑 *Stop Loss:* Colócalo unos pips por encima de la última resistencia"
        " reciente.\n"
        "🎯 *Take Profit:* Busca un objetivo con una relación de riesgo/beneficio"
        " favorable (1:2)."
    )
  else:
    mensaje += "⚪ ⏳ **ACCIÓN EXACTA: NO OPERAR (ESPERAR)** ⏳\n"
    mensaje += (
        "👉 *Qué hacer:* El mercado está en rango o sin una dirección clara."
        " **NO COMPRES NI VENDAS** en este momento.\n"
        "🛡 *Protección:* Guarda tu capital y espera al siguiente informe de la"
        " hora para ver si rompe la tendencia."
    )

  return mensaje


# Crear botones interactivos
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
      " pedir tu orden exacta en cualquier momento:"
  )
  bot.send_message(
      message.chat.id, texto, reply_markup=crear_menu(), parse_mode="Markdown"
  )


@bot.callback_query_handler(func=lambda call: True)
def manejar_botones(call):
  if call.data == "solicitar_analisis":
    bot.answer_callback_query(call.id, "Actualizando precio y orden...")
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
        "📋 *REGLAS DE ORO ANTES DE EJECUTAR*\n\n1️⃣ **Disciplina:** Nunca"
        " operes si el bot dice 'NO OPERAR'. El 80% de las pérdidas ocurren por"
        " forzar operaciones en mercados laterales.\n2️⃣ **Riesgo por"
        " operación:** Arriesga como máximo el 1% o 2% de tu cuenta total.\n3️⃣"
        " **Paciencia:** Espera siempre la confirmación de la señal."
    )
    bot.send_message(
        call.message.chat.id,
        guia,
        reply_markup=crear_menu(),
        parse_mode="Markdown",
    )


# Bucle automático cada 1 hora
def bucle_automatico():
  while True:
    time.sleep(3600)  # Cada 1 hora exacta
    try:
      informe = obtener_analisis()
      mensaje_final = (
          "⏰ *INFORME AUTOMÁTICO DE CADA HORA*\n\n" + informe
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
  hilo_hora = threading.Thread(target=bucle_automatico, daemon=True)
  hilo_hora.start()

  print("Bot actualizado con órdenes exactas funcionando...")
  bot.infinity_polling()
