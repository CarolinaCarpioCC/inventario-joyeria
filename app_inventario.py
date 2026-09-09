import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
import io

st.set_page_config(page_title="Control de Inventario - Joyería", layout="wide")

# --- CONEXIÓN Y ESTRUCTURA DE BD ---
def obtener_conexion():
    return sqlite3.connect("inventario_joyeria.db")

def inicializar_bd():
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mes_ingreso TEXT,
            lote_ingreso TEXT,
            fecha_ingreso TEXT,
            nro_sec INTEGER UNIQUE,
            codigo_programa TEXT,
            publico TEXT,
            tipo_producto TEXT,
            categoria TEXT,
            descripcion TEXT,
            color TEXT,
            gramos REAL,
            mm REAL,
            largo REAL,
            ct REAL,
            costo_oro_gramo REAL,
            costo_diamante REAL,
            venta_diamante REAL,
            total_pieza_costo REAL,
            estatus TEXT DEFAULT 'Existe',
            nro_factura TEXT,
            fecha_egreso TEXT,
            mes_egreso TEXT
        )
    """)
    conn.commit()
    conn.close()

def obtener_ultimo_estado():
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT fecha_ingreso, lote_ingreso, nro_sec FROM inventario ORDER BY id DESC LIMIT 1")
    fila = cursor.fetchone()
    conn.close()
    if fila:
        return fila[0], fila[1], fila[2]
    return None, "Lote-011", 1122

def calcular_nuevo_lote(fecha_actual_str, ultima_fecha, ultimo_lote):
    if not ultimo_lote:
        return "Lote-001"
    if ultima_fecha == fecha_actual_str:
        return ultimo_lote
    try:
        num = int(ultimo_lote.split("-")[1]) + 1
    except (IndexError, ValueError):
        num = 1
    return f"Lote-{num:03d}"

inicializar_bd()

# --- LISTAS MAESTRAS ---
OPCIONES_PUBLICO = ["Dama", "Unisex", "Caballero", "JDama"]
OPCIONES_TIPO = ["Oro", "Plata", "Diamante"]
OPCIONES_CATEGORIA = [
    "Collar", "Cadena", "Tifany", "Fancy", "Tiffany", "Rosario", 
    "Anillo", "Brazalete", "Cordon", "Argolla", "Zarcillos", "Dije", 
    "Figaro", "Espiga", "Rolo", "Tejido", "Diamante", "Lingote", "Medalla", "Monedas"
]
OPCIONES_COLOR = ["Amarillo", "Blanco", "Rosado", "Combinado"]
OPCIONES_ESTATUS = ["Existe", "Venta D", "Venta M", "Apartado", "Ajuste"]

PREFIJOS_PUB = {"Dama": "D", "Unisex": "U", "Caballero": "C", "JDama": "JD"}
PREFIJOS_CAT = {
    "Collar": "CO", "Cadena": "CJ", "Lingote": "LU", "Brazalete": "BU", 
    "Anillo": "AN", "Zarcillos": "ZA", "Dije": "DI", "Cordon": "CR"
}

st.title("💎 Sistema de Control de Inventario - Joyería")

tab_ingreso, tab_modificar = st.tabs(["➕ Ingresar Productos", "✏️ Modificar / Ajustar Piezas"])

# ==========================================
# 1. PESTAÑA: INGRESAR PRODUCTOS
# ==========================================
with tab_ingreso:
    if "form_version" not in st.session_state:
        st.session_state.form_version = 0
    if "mostrar_confirmacion" not in st.session_state:
        st.session_state.mostrar_confirmacion = False
    if "datos_pendientes" not in st.session_state:
        st.session_state.datos_pendientes = None

    v = st.session_state.form_version

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        cantidades = st.number_input("Cantidad de Artículos *", min_value=0, step=1, value=0, key=f"cant_{v}")
        fecha_ingreso = st.date_input("Fecha Ingreso *", value=date.today(), key=f"fecha_{v}")
        publico = st.selectbox("Público *", OPCIONES_PUBLICO, index=None, placeholder="Seleccione público...", key=f"pub_{v}")
        tipo_producto = st.selectbox("Tipo Producto *", OPCIONES_TIPO, index=None, placeholder="Seleccione tipo...", key=f"tipo_{v}")

    es_metal = (tipo_producto in ["Oro", "Plata"])
    es_diamante = (tipo_producto == "Diamante")

    with c2:
        categoria = st.selectbox("Categoría *", OPCIONES_CATEGORIA, index=None, placeholder="Seleccione categoría...", key=f"cat_{v}")
        descripcion = st.text_input("Descripción *", placeholder="Ej. Tiffany, Lingotes 2.5...", key=f"desc_{v}")
        color = st.selectbox("Color *", OPCIONES_COLOR, index=None, placeholder="Seleccione color...", key=f"color_{v}")
        gramos = st.number_input("Gramos *" if es_metal else "Gramos", min_value=0.0, step=0.01, format="%.2f", value=0.00, disabled=not es_metal, key=f"gr_{v}")

    with c3:
        mm = st.number_input("MM.", min_value=0.0, step=0.01, format="%.2f", value=0.00, disabled=not es_metal, key=f"mm_{v}")
        largo = st.number_input("Largo", min_value=0.0, step=0.01, format="%.2f", value=0.00, disabled=not es_metal, key=f"lar_{v}")
        ct = st.number_input("Ct *" if es_diamante else "Ct", min_value=0.0, step=0.01, format="%.2f", value=0.00, disabled=not es_diamante, key=f"ct_{v}")
        costo_oro_gramo = st.number_input("Costo Oro por Gramo ($) *" if es_metal else "Costo Oro por Gramo ($)", min_value=0.0, step=0.01, format="%.2f", value=0.00, disabled=not es_metal, key=f"cog_{v}")

    with c4:
        costo_diamante = st.number_input("Costo Diamante por Pieza ($) *" if es_diamante else "Costo Diamante por Pieza ($)", min_value=0.0, step=0.01, format="%.2f", value=0.00, disabled=not es_diamante, key=f"cd_{v}")
        venta_diamante = st.number_input("Venta Diamante por Pieza ($)", min_value=0.0, step=0.01, format="%.2f", value=0.00, disabled=not es_diamante, key=f"vd_{v}")
        
        costo_estimado = (gramos * costo_oro_gramo) if es_metal else (costo_diamante if es_diamante else 0.0)
        st.metric("Total Costo estimado/pieza", f"${costo_estimado:,.2f}")
        
        st.write("")
        btn_revisar = st.button("Revisar y Validar Ingreso", type="primary", width="stretch")

    if btn_revisar:
        errores = []
        if cantidades <= 0:
            errores.append("La **Cantidad de Artículos** debe ser mayor a 0.")
        if not fecha_ingreso:
            errores.append("Debe seleccionar una **Fecha de Ingreso** válida.")
        if not publico:
            errores.append("Debe seleccionar una opción en **Público**.")
        if not tipo_producto:
            errores.append("Debe seleccionar un **Tipo de Producto**.")
        if not categoria:
            errores.append("Debe seleccionar una **Categoría**.")
        if not descripcion.strip():
            errores.append("El campo **Descripción** es obligatorio.")
        if not color:
            errores.append("Debe seleccionar un **Color**.")
            
        if es_metal:
            if gramos <= 0:
                errores.append(f"Para productos de {tipo_producto}, los **Gramos** deben ser mayores a 0.00.")
            if costo_oro_gramo <= 0:
                errores.append(f"Debe ingresar el **Costo por Gramo** de {tipo_producto} mayor a $0.00.")
        if es_diamante:
            if ct <= 0:
                errores.append("Para piezas de **Diamante**, el campo **Ct** debe ser mayor a 0.00.")
            if costo_diamante <= 0:
                errores.append("Debe ingresar el **Costo Diamante por Pieza** mayor a $0.00.")

        if errores:
            for err in errores:
                st.error(f"⚠️ {err}")
            st.session_state.mostrar_confirmacion = False
        else:
            fecha_str = str(fecha_ingreso)
            meses_es = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            mes_str = meses_es[fecha_ingreso.month - 1]
            
            ult_fecha, ult_lote, ult_sec = obtener_ultimo_estado()
            lote_a_usar = calcular_nuevo_lote(fecha_str, ult_fecha, ult_lote)
            
            val_gramos = gramos if es_metal else 0.0
            val_mm = mm if es_metal else 0.0
            val_largo = largo if es_metal else 0.0
            val_costo_gr = costo_oro_gramo if es_metal else 0.0
            val_ct = ct if es_diamante else 0.0
            val_costo_d = costo_diamante if es_diamante else 0.0
            val_venta_d = venta_diamante if es_diamante else 0.0
            costo_pieza = round((val_gramos * val_costo_gr) + val_costo_d, 2)
            pref_c = PREFIJOS_CAT.get(categoria, categoria[:2].upper())
            
            st.session_state.datos_pendientes = {
                "cantidades": cantidades, "mes_str": mes_str, "lote_a_usar": lote_a_usar,
                "fecha_str": fecha_str, "ult_sec": ult_sec, "pref_c": pref_c,
                "publico": publico, "tipo_producto": tipo_producto, "categoria": categoria,
                "descripcion": descripcion.strip(), "color": color, "gramos": val_gramos,
                "mm": val_mm, "largo": val_largo, "ct": val_ct, "costo_oro_gramo": val_costo_gr,
                "costo_diamante": val_costo_d, "venta_diamante": val_venta_d,
                "costo_pieza": costo_pieza, "total_inversion": round(costo_pieza * cantidades, 2)
            }
            st.session_state.mostrar_confirmacion = True

    if st.session_state.mostrar_confirmacion and st.session_state.datos_pendientes:
        p = st.session_state.datos_pendientes
        sec_ini = p['ult_sec'] + 1
        sec_fin = p['ult_sec'] + p['cantidades']

        st.warning("⚠️ **Verificación previa:** Revisa cuidadosamente los datos antes de guardarlos de forma definitiva.")
        with st.container(border=True):
            st.markdown("### Resumen de Ingreso al Inventario")
            col_res1, col_res2, col_res3 = st.columns(3)
            with col_res1:
                st.write(f"**Lote asignado:** `{p['lote_a_usar']}`")
                st.write(f"**Fecha Ingreso:** `{p['fecha_str']}` ({p['mes_str']})")
                st.write(f"**Cantidad:** `{p['cantidades']} piezas`")
            with col_res2:
                st.write(f"**Secuencias:** `{sec_ini}` a `{sec_fin}`")
                st.write(f"**Producto:** `{p['tipo_producto']}` - `{p['categoria']}`")
                st.write(f"**Descripción:** `{p['descripcion']}` ({p['color']})")
            with col_res3:
                st.write(f"**Público:** `{p['publico']}`")
                st.write(f"**Costo por Pieza:** `${p['costo_pieza']:,.2f}`")
                st.write(f"**Inversión Total Lote:** `${p['total_inversion']:,.2f}`")

            filas_previa = []
            for i in range(p['cantidades']):
                s = sec_ini + i
                filas_previa.append({
                    "Lote": p['lote_a_usar'], "Fecha": p['fecha_str'], "Nro Sec.": s,
                    "Código": f"UG-{p['pref_c']}-{s}", "Descripción": p['descripcion'],
                    "Gramos": p['gramos'], "Costo/Pieza ($)": p['costo_pieza']
                })
            st.dataframe(pd.DataFrame(filas_previa), width="stretch", hide_index=True)
            
            c_btn1, c_btn2, _ = st.columns([1, 1, 2])
            with c_btn1:
                btn_confirmar = st.button("✅ Confirmar y Guardar", type="primary", width="stretch")
            with c_btn2:
                btn_cancelar = st.button("❌ Cancelar", width="stretch")

        if btn_confirmar:
            conn = obtener_conexion()
            cursor = conn.cursor()
            registros = []
            for i in range(p['cantidades']):
                sec = sec_ini + i
                cod = f"UG-{p['pref_c']}-{sec}"
                registros.append((
                    p['mes_str'], p['lote_a_usar'], p['fecha_str'], sec, cod,
                    p['publico'], p['tipo_producto'], p['categoria'], p['descripcion'], p['color'],
                    p['gramos'], p['mm'], p['largo'], p['ct'], p['costo_oro_gramo'], p['costo_diamante'],
                    p['venta_diamante'], p['costo_pieza'], "Existe"
                ))
            cursor.executemany("""
                INSERT INTO inventario (
                    mes_ingreso, lote_ingreso, fecha_ingreso, nro_sec, codigo_programa,
                    publico, tipo_producto, categoria, descripcion, color,
                    gramos, mm, largo, ct, costo_oro_gramo, costo_diamante,
                    venta_diamante, total_pieza_costo, estatus
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, registros)
            conn.commit()
            conn.close()
            
            st.session_state.mostrar_confirmacion = False
            st.session_state.datos_pendientes = None
            st.session_state.form_version += 1
            st.success(f"✅ ¡Guardado exitoso! Se crearon las piezas en el {p['lote_a_usar']}.")
            st.rerun()
            
        if btn_cancelar:
            st.session_state.mostrar_confirmacion = False
            st.session_state.datos_pendientes = None
            st.session_state.form_version += 1
            st.info("Operación cancelada. El formulario ha sido limpiado.")
            st.rerun()

# ==========================================
# 2. PESTAÑA: MODIFICAR / AJUSTAR PIEZAS Y LOTES
# ==========================================
with tab_modificar:
    modo_edicion = st.radio(
        "Modalidad de Modificación:",
        ["🎯 Modificar por Pieza Individual", "📦 Modificar Lote Completo (Masivo)"],
        horizontal=True
    )
    
    conn = obtener_conexion()
    
    # ----------------------------------------------------
    # OPCIÓN A: MODIFICAR POR PIEZA INDIVIDUAL
    # ----------------------------------------------------
    if modo_edicion == "🎯 Modificar por Pieza Individual":
        st.subheader("Localizar Pieza Individual")
        df_lista = pd.read_sql_query("SELECT nro_sec, codigo_programa, descripcion, lote_ingreso, estatus FROM inventario ORDER BY nro_sec DESC", conn)
        
        if df_lista.empty:
            st.info("No hay registros en la base de datos para modificar.")
        else:
            opciones_piezas = [f"{row['nro_sec']} | {row['codigo_programa']} | {row['descripcion']} ({row['estatus']})" for _, row in df_lista.iterrows()]
            pieza_seleccionada = st.selectbox("Seleccione la pieza que desea ajustar o editar:", opciones_piezas, index=0)
            sec_elegida = int(pieza_seleccionada.split(" | ")[0])
            
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM inventario WHERE nro_sec = ?", (sec_elegida,))
            datos_pieza = cursor.fetchone()
            
            st.markdown(f"#### Editando Pieza: `{datos_pieza[5]}` (Secuencia: `{datos_pieza[4]}` - Lote: `{datos_pieza[2]}`)")
            
            with st.container(border=True):
                e1, e2, e3, e4 = st.columns(4)
                with e1:
                    idx_pub = OPCIONES_PUBLICO.index(datos_pieza[6]) if datos_pieza[6] in OPCIONES_PUBLICO else 0
                    nuevo_publico = st.selectbox("Público", OPCIONES_PUBLICO, index=idx_pub, key="ind_pub")
                    idx_tipo = OPCIONES_TIPO.index(datos_pieza[7]) if datos_pieza[7] in OPCIONES_TIPO else 0
                    nuevo_tipo = st.selectbox("Tipo Producto", OPCIONES_TIPO, index=idx_tipo, key="ind_tipo")
                    idx_est = OPCIONES_ESTATUS.index(datos_pieza[19]) if datos_pieza[19] in OPCIONES_ESTATUS else 0
                    nuevo_estatus = st.selectbox("Estatus de la Pieza", OPCIONES_ESTATUS, index=idx_est, key="ind_est")
                    
                with e2:
                    idx_cat = OPCIONES_CATEGORIA.index(datos_pieza[8]) if datos_pieza[8] in OPCIONES_CATEGORIA else 0
                    nueva_categoria = st.selectbox("Categoría", OPCIONES_CATEGORIA, index=idx_cat, key="ind_cat")
                    nueva_descripcion = st.text_input("Descripción", value=datos_pieza[9], key="ind_desc")
                    idx_col = OPCIONES_COLOR.index(datos_pieza[10]) if datos_pieza[10] in OPCIONES_COLOR else 0
                    nuevo_color = st.selectbox("Color", OPCIONES_COLOR, index=idx_col, key="ind_col")

                edit_es_metal = (nuevo_tipo in ["Oro", "Plata"])
                edit_es_diamante = (nuevo_tipo == "Diamante")

                with e3:
                    nuevos_gramos = st.number_input("Gramos", min_value=0.0, step=0.01, format="%.2f", value=float(datos_pieza[11]), disabled=not edit_es_metal, key="ind_gr")
                    nuevos_mm = st.number_input("MM.", min_value=0.0, step=0.01, format="%.2f", value=float(datos_pieza[12]), disabled=not edit_es_metal, key="ind_mm")
                    nuevo_largo = st.number_input("Largo", min_value=0.0, step=0.01, format="%.2f", value=float(datos_pieza[13]), disabled=not edit_es_metal, key="ind_lar")
                    nuevos_ct = st.number_input("Ct", min_value=0.0, step=0.01, format="%.2f", value=float(datos_pieza[14]), disabled=not edit_es_diamante, key="ind_ct")

                with e4:
                    nuevo_costo_gr = st.number_input("Costo Oro por Gramo ($)", min_value=0.0, step=0.01, format="%.2f", value=float(datos_pieza[15]), disabled=not edit_es_metal, key="ind_cog")
                    nuevo_costo_d = st.number_input("Costo Diamante ($)", min_value=0.0, step=0.01, format="%.2f", value=float(datos_pieza[16]), disabled=not edit_es_diamante, key="ind_cd")
                    nueva_venta_d = st.number_input("Venta Diamante ($)", min_value=0.0, step=0.01, format="%.2f", value=float(datos_pieza[17]), disabled=not edit_es_diamante, key="ind_vd")
                    fact_actual = datos_pieza[20] if datos_pieza[20] else ""
                    nuevo_nro_factura = st.text_input("Nro Factura (Si egresó)", value=fact_actual, key="ind_fact")

                if edit_es_metal:
                    costo_recalculado = round(nuevos_gramos * nuevo_costo_gr, 2)
                elif edit_es_diamante:
                    costo_recalculado = round(nuevo_costo_d, 2)
                else:
                    costo_recalculado = 0.0

                st.write(f"**Nuevo Costo Total de la Pieza:** `${costo_recalculado:,.2f}`")
                btn_guardar_ajuste = st.button("💾 Guardar Cambios en la Pieza", type="primary", width="stretch")
                
                if btn_guardar_ajuste:
                    cursor.execute("""
                        UPDATE inventario SET
                            publico = ?, tipo_producto = ?, categoria = ?, descripcion = ?,
                            color = ?, gramos = ?, mm = ?, largo = ?, ct = ?,
                            costo_oro_gramo = ?, costo_diamante = ?, venta_diamante = ?,
                            total_pieza_costo = ?, estatus = ?, nro_factura = ?
                        WHERE nro_sec = ?
                    """, (
                        nuevo_publico, nuevo_tipo, nueva_categoria, nueva_descripcion.strip(),
                        nuevo_color, nuevos_gramos, nuevos_mm, nuevo_largo, nuevos_ct,
                        nuevo_costo_gr, nuevo_costo_d, nueva_venta_d, costo_recalculado,
                        nuevo_estatus, nuevo_nro_factura.strip(), sec_elegida
                    ))
                    conn.commit()
                    st.success(f"✅ ¡Pieza {sec_elegida} actualizada exitosamente!")
                    st.rerun()

    # ----------------------------------------------------
    # OPCIÓN B: MODIFICAR LOTE COMPLETO (MASIVO)
    # ----------------------------------------------------
    else:
        st.subheader("Modificación Masiva por Lote")
        df_lotes = pd.read_sql_query("SELECT DISTINCT lote_ingreso FROM inventario ORDER BY lote_ingreso DESC", conn)
        
        if df_lotes.empty:
            st.info("No hay lotes registrados para modificar.")
        else:
            lista_lotes = df_lotes['lote_ingreso'].tolist()
            lote_seleccionado = st.selectbox("Seleccione el Lote a modificar en bloque:", lista_lotes)
            
            # Obtener datos promedio/referenciales de ese lote
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM inventario WHERE lote_ingreso = ? ORDER BY id ASC LIMIT 1", (lote_seleccionado,))
            muestra_lote = cursor.fetchone()
            
            cursor.execute("SELECT COUNT(*) FROM inventario WHERE lote_ingreso = ?", (lote_seleccionado,))
            total_piezas_lote = cursor.fetchone()[0]
            
            st.warning(f"⚠️ **Atención:** Cualquier cambio que apliques aquí afectará a las **{total_piezas_lote} piezas** registradas en el `{lote_seleccionado}`.")
            
            with st.container(border=True):
                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    idx_pub_m = OPCIONES_PUBLICO.index(muestra_lote[6]) if muestra_lote[6] in OPCIONES_PUBLICO else 0
                    lote_publico = st.selectbox("Público", OPCIONES_PUBLICO, index=idx_pub_m, key="lot_pub")
                    idx_tipo_m = OPCIONES_TIPO.index(muestra_lote[7]) if muestra_lote[7] in OPCIONES_TIPO else 0
                    lote_tipo = st.selectbox("Tipo Producto", OPCIONES_TIPO, index=idx_tipo_m, key="lot_tipo")
                    idx_est_m = OPCIONES_ESTATUS.index(muestra_lote[19]) if muestra_lote[19] in OPCIONES_ESTATUS else 0
                    lote_estatus = st.selectbox("Estatus general", OPCIONES_ESTATUS, index=idx_est_m, key="lot_est")

                lote_es_metal = (lote_tipo in ["Oro", "Plata"])
                lote_es_diamante = (lote_tipo == "Diamante")

                with m2:
                    idx_cat_m = OPCIONES_CATEGORIA.index(muestra_lote[8]) if muestra_lote[8] in OPCIONES_CATEGORIA else 0
                    lote_categoria = st.selectbox("Categoría", OPCIONES_CATEGORIA, index=idx_cat_m, key="lot_cat")
                    lote_descripcion = st.text_input("Descripción", value=muestra_lote[9], key="lot_desc")
                    idx_col_m = OPCIONES_COLOR.index(muestra_lote[10]) if muestra_lote[10] in OPCIONES_COLOR else 0
                    lote_color = st.selectbox("Color", OPCIONES_COLOR, index=idx_col_m, key="lot_col")

                with m3:
                    lote_gramos = st.number_input("Gramos (por pieza)", min_value=0.0, step=0.01, format="%.2f", value=float(muestra_lote[11]), disabled=not lote_es_metal, key="lot_gr")
                    lote_mm = st.number_input("MM.", min_value=0.0, step=0.01, format="%.2f", value=float(muestra_lote[12]), disabled=not lote_es_metal, key="lot_mm")
                    lote_largo = st.number_input("Largo", min_value=0.0, step=0.01, format="%.2f", value=float(muestra_lote[13]), disabled=not lote_es_metal, key="lot_lar")
                    lote_ct = st.number_input("Ct", min_value=0.0, step=0.01, format="%.2f", value=float(muestra_lote[14]), disabled=not lote_es_diamante, key="lot_ct")

                with m4:
                    lote_costo_gr = st.number_input("Costo Oro por Gramo ($)", min_value=0.0, step=0.01, format="%.2f", value=float(muestra_lote[15]), disabled=not lote_es_metal, key="lot_cog")
                    lote_costo_d = st.number_input("Costo Diamante ($)", min_value=0.0, step=0.01, format="%.2f", value=float(muestra_lote[16]), disabled=not lote_es_diamante, key="lot_cd")
                    lote_venta_d = st.number_input("Venta Diamante ($)", min_value=0.0, step=0.01, format="%.2f", value=float(muestra_lote[17]), disabled=not lote_es_diamante, key="lot_vd")
                    
                if lote_es_metal:
                    nuevo_costo_pieza_lote = round(lote_gramos * lote_costo_gr, 2)
                elif lote_es_diamante:
                    nuevo_costo_pieza_lote = round(lote_costo_d, 2)
                else:
                    nuevo_costo_pieza_lote = 0.0

                st.write(f"**Nuevo Costo Resultante por Pieza:** `${nuevo_costo_pieza_lote:,.2f}` | **Nuevo Total Inversión Lote:** `${(nuevo_costo_pieza_lote * total_piezas_lote):,.2f}`")
                
                btn_actualizar_lote = st.button(f"🚀 Actualizar Todas las {total_piezas_lote} Piezas del {lote_seleccionado}", type="primary", width="stretch")
                
                if btn_actualizar_lote:
                    pref_c = PREFIJOS_CAT.get(lote_categoria, lote_categoria[:2].upper())
                    
                    # Actualizar todas las filas del lote y regenerar el código con el nuevo prefijo de categoría
                    cursor.execute("""
                        UPDATE inventario SET
                            publico = ?,
                            tipo_producto = ?,
                            categoria = ?,
                            codigo_programa = 'UG-' || ? || '-' || nro_sec,
                            descripcion = ?,
                            color = ?,
                            gramos = ?,
                            mm = ?,
                            largo = ?,
                            ct = ?,
                            costo_oro_gramo = ?,
                            costo_diamante = ?,
                            venta_diamante = ?,
                            total_pieza_costo = ?,
                            estatus = ?
                        WHERE lote_ingreso = ?
                    """, (
                        lote_publico, lote_tipo, lote_categoria, pref_c,
                        lote_descripcion.strip(), lote_color, lote_gramos, lote_mm,
                        lote_largo, lote_ct, lote_costo_gr, lote_costo_d,
                        lote_venta_d, nuevo_costo_pieza_lote, lote_estatus, lote_seleccionado
                    ))
                    conn.commit()
                    st.success(f"✅ ¡Se actualizaron con éxito las {total_piezas_lote} piezas pertenecientes al {lote_seleccionado}!")
                    st.rerun()

    conn.close()

st.divider()

# --- TABLA GENERAL Y EXPORTACIÓN ---
st.subheader("📋 Existencias y Registros Actuales")

conn = obtener_conexion()
df = pd.read_sql_query("""
    SELECT 
        lote_ingreso AS 'Lote',
        fecha_ingreso AS 'Fecha',
        estatus AS 'Estatus',
        nro_sec AS 'Sec.',
        codigo_programa AS 'Código',
        publico AS 'Público',
        tipo_producto AS 'Tipo',
        categoria AS 'Categoría',
        descripcion AS 'Descripción',
        color AS 'Color',
        gramos AS 'Gr.',
        mm AS 'MM.',
        largo AS 'Largo',
        ct AS 'Ct',
        costo_oro_gramo AS 'Costo/Gr ($)',
        costo_diamante AS 'Costo Diam ($)',
        total_pieza_costo AS 'Total Costo ($)',
        nro_factura AS 'Factura'
    FROM inventario 
    ORDER BY id DESC
""", conn)
conn.close()

if not df.empty:
    st.dataframe(df, width="stretch", hide_index=True)
    
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventario')
    
    st.download_button(
        label="📥 Descargar Inventario Completo en Excel",
        data=buf.getvalue(),
        file_name="Inventario_Joyeria.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("No hay piezas en el inventario aún.")