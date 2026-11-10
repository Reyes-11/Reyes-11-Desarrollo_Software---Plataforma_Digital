"""Plataforma de gestión técnica y auditoría de NAP FTTH-GPON - Municipio Plaza (Guarenas), Miranda.
Ejecutar: python app.py  ->  http://127.0.0.1:5000"""
import csv, io, os
from datetime import datetime
from decimal import Decimal
import pymysql
from pymysql.cursors import DictCursor
from flask import Flask, Response, jsonify, request

app = Flask(__name__, static_folder="static", static_url_path="/static")
CFG = dict(host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "3306")),
           user=os.getenv("DB_USER", "root"), password=os.getenv("DB_PASSWORD", ""),
           database=os.getenv("DB_NAME", "nap_plaza"), cursorclass=DictCursor,
           autocommit=True, charset="utf8mb4")

# Parámetros ITU-T G.984 (GPON clase B+): presupuesto ~28 dB, sensibilidad ONT -27 dBm, sobrecarga -8 dBm
SPLITTER_LOSS = {"1:2": 3.7, "1:4": 7.3, "1:8": 10.5, "1:16": 13.8, "1:32": 17.1, "1:64": 20.5}
FIBER_DB_KM, CONNECTOR_DB, SPLICE_DB = 0.25, 0.5, 0.1   # 1490 nm (downstream)
RX_MAX, RX_WARN, RX_MIN, DEVIATION = -8.0, -25.0, -27.0, 3.0


class ApiError(Exception):
    def __init__(self, msg, code=400): self.msg, self.code = msg, code


@app.errorhandler(ApiError)
def _api_err(e): return jsonify(error=e.msg), e.code

@app.errorhandler(pymysql.err.IntegrityError)
def _integrity(e): return jsonify(error="Registro duplicado o dato inválido (¿código de NAP repetido?)"), 409

@app.errorhandler(pymysql.err.MySQLError)
def _db(e): return jsonify(error=f"Error de base de datos: {e}"), 500


def clean(x):
    if isinstance(x, list): return [clean(i) for i in x]
    if isinstance(x, dict): return {k: clean(v) for k, v in x.items()}
    if isinstance(x, Decimal): return float(x)
    if isinstance(x, datetime): return x.strftime("%Y-%m-%d %H:%M")
    return x


def db(sql, args=(), one=False, write=False):
    con = pymysql.connect(**CFG)
    try:
        with con.cursor() as c:
            c.execute(sql, args)
            if write: return c.lastrowid
            rows = c.fetchall()
            return clean(rows[0] if rows else None) if one else clean(list(rows))
    finally:
        con.close()


def num(d, key, lo, hi, label, integer=False):
    try: v = float(d.get(key))
    except (TypeError, ValueError): raise ApiError(f"{label} debe ser numérico")
    if not lo <= v <= hi: raise ApiError(f"{label} debe estar entre {lo} y {hi}")
    return int(v) if integer else v


def budget(nap, connectors, splices):
    loss = nap["distance_km"] * FIBER_DB_KM + SPLITTER_LOSS[nap["splitter"]] + connectors * CONNECTOR_DB + splices * SPLICE_DB
    return round(loss, 2), round(nap["olt_tx_dbm"] - loss, 2)


def classify(rx, expected):
    if rx > RX_MAX: return "CRITICO", "Saturación del receptor ONT: potencia sobre -8 dBm. Instalar atenuador."
    if rx < RX_MIN: return "CRITICO", "Potencia bajo la sensibilidad de la ONT (-27 dBm). Revisar corte, curvatura o conector sucio."
    if rx < RX_WARN: return "ALERTA", "Margen mínimo: potencia entre -25 y -27 dBm. Programar mantenimiento."
    if expected - rx > DEVIATION:
        return "ALERTA", f"Pérdida real {expected - rx:.1f} dB mayor a la teórica: revisar empalmes, conectores y macrocurvaturas."
    return "OK", "Enlace dentro de los parámetros GPON clase B+."


def get_nap(nap_id):
    nap = db("SELECT * FROM naps WHERE id=%s", (nap_id,), one=True)
    if not nap: raise ApiError("NAP no encontrada", 404)
    return nap


def nap_data(d):
    code, sector = str(d.get("code", "")).strip().upper(), str(d.get("sector", "")).strip()
    if not code or not sector: raise ApiError("Código y sector son obligatorios")
    splitter = d.get("splitter")
    if splitter not in SPLITTER_LOSS: raise ApiError("Splitter no válido")
    total = num(d, "ports_total", 1, 64, "Puertos totales", True)
    if total > int(splitter.split(":")[1]): raise ApiError("Los puertos exceden las salidas del splitter")
    used = num(d, "ports_used", 0, 64, "Puertos usados", True)
    if used > total: raise ApiError("Puertos usados no puede superar los totales")
    state = d.get("state", "Activa")
    if state not in ("Activa", "Mantenimiento", "Inactiva"): raise ApiError("Estado no válido")
    return (code, sector, str(d.get("address", ""))[:200], splitter, total, used,
            num(d, "olt_tx_dbm", -5, 10, "Potencia OLT"), num(d, "distance_km", 0, 20, "Distancia (km)"),
            state, str(d.get("notes", ""))[:255])

NAP_COLS = "code,sector,address,splitter,ports_total,ports_used,olt_tx_dbm,distance_km,state,notes"


@app.get("/")
def index(): return app.send_static_file("index.html")


@app.get("/api/naps")
def naps_list():
    return jsonify(db("SELECT n.*, (SELECT status FROM audits a WHERE a.nap_id=n.id ORDER BY a.id DESC LIMIT 1) AS last_status "
                      "FROM naps n ORDER BY n.code"))


@app.post("/api/naps")
def naps_create():
    nid = db(f"INSERT INTO naps ({NAP_COLS}) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", nap_data(request.get_json(force=True)), write=True)
    return jsonify(id=nid), 201


@app.put("/api/naps/<int:nid>")
def naps_update(nid):
    get_nap(nid)
    sets = ",".join(f"{c}=%s" for c in NAP_COLS.split(","))
    db(f"UPDATE naps SET {sets} WHERE id=%s", nap_data(request.get_json(force=True)) + (nid,), write=True)
    return jsonify(ok=True)


@app.delete("/api/naps/<int:nid>")
def naps_delete(nid):
    get_nap(nid); db("DELETE FROM naps WHERE id=%s", (nid,), write=True)
    return jsonify(ok=True)


def audit_calc(d):
    nap = get_nap(int(d.get("nap_id", 0) or 0))
    c, s = num(d, "connectors", 0, 20, "Conectores", True), num(d, "splices", 0, 50, "Empalmes", True)
    loss, expected = budget(nap, c, s)
    return nap, c, s, loss, expected


@app.post("/api/calc")
def calc():
    _, _, _, loss, expected = audit_calc(request.get_json(force=True))
    return jsonify(loss_db=loss, expected_dbm=expected)


@app.post("/api/audits")
def audits_create():
    d = request.get_json(force=True)
    tech = str(d.get("technician", "")).strip()
    if not tech: raise ApiError("El nombre del técnico es obligatorio")
    nap, c, s, loss, expected = audit_calc(d)
    rx = num(d, "rx_dbm", -50, 5, "Potencia medida (dBm)")
    status, diag = classify(rx, expected)
    aid = db("INSERT INTO audits (nap_id,technician,rx_dbm,connectors,splices,expected_dbm,loss_db,status,diagnosis) "
             "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", (nap["id"], tech[:80], rx, c, s, expected, loss, status, diag), write=True)
    return jsonify(id=aid, status=status, diagnosis=diag, expected_dbm=expected), 201


AUDIT_SQL = ("SELECT a.*, n.code, n.sector FROM audits a JOIN naps n ON n.id=a.nap_id "
             "{w} ORDER BY a.id DESC LIMIT 500")

@app.get("/api/audits")
def audits_list():
    st = request.args.get("status")
    if st in ("OK", "ALERTA", "CRITICO"): return jsonify(db(AUDIT_SQL.format(w="WHERE a.status=%s"), (st,)))
    return jsonify(db(AUDIT_SQL.format(w="")))


@app.get("/api/stats")
def stats():
    row = db("SELECT COUNT(*) naps, COALESCE(SUM(ports_total),0) pt, COALESCE(SUM(ports_used),0) pu FROM naps", one=True)
    last = db("SELECT a.status, COUNT(*) n FROM audits a JOIN (SELECT MAX(id) id FROM audits GROUP BY nap_id) m ON m.id=a.id GROUP BY a.status")
    by = {r["status"]: r["n"] for r in last}
    return jsonify(naps=row["naps"], ports_total=int(row["pt"]), ports_used=int(row["pu"]),
                   audits=db("SELECT COUNT(*) n FROM audits", one=True)["n"],
                   ok=by.get("OK", 0), alerta=by.get("ALERTA", 0), critico=by.get("CRITICO", 0))


@app.get("/api/export.csv")
def export():
    rows = db(AUDIT_SQL.format(w=""))
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(["Fecha", "NAP", "Sector", "Tecnico", "Rx dBm", "Esperada dBm", "Perdida dB", "Estado", "Diagnostico"])
    for r in rows: w.writerow([r["created_at"], r["code"], r["sector"], r["technician"], r["rx_dbm"], r["expected_dbm"], r["loss_db"], r["status"], r["diagnosis"]])
    return Response("\ufeff" + out.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=auditorias_nap.csv"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
