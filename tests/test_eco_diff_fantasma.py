"""Regresion: el diff de ECO marcaba ~500 MODIFY fantasma (ver control de BOM)."""
from app.api.informacion_basica.control_bom_data import (
    _eco_component_tuple,
    _eco_diff_field_value,
    _eco_path_keys,
)

VALID_FROM_IDX = 16
REMARK_IDX = 26


def _tuple_for(item, added_keys=()):
    eco = {'eco_no': 'SUSTITUTOS'}
    return _eco_component_tuple('EBR41039117', '05', item, '2026-08-20', eco, 1, added_keys)


def test_eco_diff_no_marca_cambios_fantasma():
    # valid_to: KS manda el centinela 9999-12-31, la BD guarda NULL -> no es un cambio
    assert _eco_diff_field_value({'valid_to': '9999-12-31'}, 'valid_to') == ''
    assert _eco_diff_field_value({'valid_to': None}, 'valid_to') == ''
    assert _eco_diff_field_value({'valid_to': '2026-07-01'}, 'valid_to') == '2026-07-01'

    # multi-valor: mismo contenido en distinto orden/espaciado -> no es un cambio
    for field in ('maker', 'alt_item_no', 'alt_spec', 'alt_maker', 'supplier'):
        a = _eco_diff_field_value({field: 'EAE66267901,0CK104BH64B'}, field)
        b = _eco_diff_field_value({field: '0CK104BH64B, EAE66267901'}, field)
        assert a == b, field
    assert (_eco_diff_field_value({'maker': 'SAMWHA'}, 'maker')
            != _eco_diff_field_value({'maker': 'FENGHUA'}, 'maker'))

    # item_process vacio del ERP = MAIN que el MES guarda al aprobar
    assert _eco_diff_field_value({'item_process': ''}, 'item_process') == _eco_diff_field_value({'item_process': 'MAIN'}, 'item_process')
    assert _eco_diff_field_value({'item_process': 'SMD'}, 'item_process') != 'MAIN'

    # fila que el ECO NO toca: conserva su valid_from y su remark reales
    carry = {'item_no': '49111007', 'bom_level': '01-01', 'valid_from': '2026-07-01', 'remark': ''}
    row = _tuple_for(carry, added_keys=set())
    assert row[VALID_FROM_IDX] == '2026-07-01', row[VALID_FROM_IDX]
    assert row[REMARK_IDX] is None, row[REMARK_IDX]

    # fila que el ECO agrega: si se sella con la fecha efectiva y el numero de ECO
    row = _tuple_for(dict(carry), added_keys={'49111007|01-01'})
    assert row[VALID_FROM_IDX] == '2026-08-20', row[VALID_FROM_IDX]
    assert row[REMARK_IDX] == 'ECO SUSTITUTOS', row[REMARK_IDX]

    # remark propio del Excel gana sobre el sello
    row = _tuple_for({**carry, 'remark': '(변경) BD1'}, added_keys={'49111007|01-01'})
    assert row[REMARK_IDX] == '(변경) BD1', row[REMARK_IDX]

    print('ok')


def test_eco_path_keys_sobrevive_renumeracion_del_erp():
    # MES: subensamble en 01-29; ERP lo movio a 01-31 -> mismas claves por ruta
    mes = [('EBR37437074_I', '01-29'), ('0TR127309AD', '01-29-01'), ('491110014', '01-30')]
    erp = [('491110014', '01-29'), ('EBR37437074_I', '01-31'), ('0TR127309AD', '01-31-01')]
    assert set(_eco_path_keys(mes)) == set(_eco_path_keys(erp))
    assert 'path:EBR37437074_I/0TR127309AD#1' in _eco_path_keys(erp)
    # mismo item bajo otro padre -> clave distinta
    assert _eco_path_keys([('A', '01-01'), ('X', '01-01-01')])[1] != _eco_path_keys([('B', '01-01'), ('X', '01-01-01')])[1]


def test_eco_from_excel_acepta_export_crudo_del_erp(monkeypatch):
    # El export del ERP trae una fila de titulo antes de los encabezados KS.
    import inspect, io
    from flask import Flask
    from openpyxl import Workbook
    from app.api.informacion_basica import control_bom as ctl

    wb = Workbook()
    ws = wb.active
    ws.append(['Summarized BOM조회(ISEMM)_ilsan'])
    ws.append(['BOM level', 'Matrl No.', 'Total Request AMT', 'Location'])
    ws.append(['01-01', 'EAH30114201', 1, 'BD1'])
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)

    captured = {}
    monkeypatch.setattr(ctl, 'crear_eco_desde_excel',
                        lambda meta, rows, user: captured.setdefault('rows', rows) and {'success': True})
    app = Flask('t')
    app.secret_key = 'x'
    with app.test_request_context('/api/ecos/from-excel', method='POST',
                                  data={'file': (bio, 'Excel_20260922074048.xlsx'), 'part_no': 'EBR30299363'}):
        body, code = inspect.unwrap(ctl.api_ecos_from_excel)()
    assert code == 201, body.get_json()
    assert [(r['bom_level'], r['item_no'], r['qty']) for r in captured['rows']] == [('01-01', 'EAH30114201', 1)]


def test_eco_aviso_muchos_cambios_no_bloquea():
    from app.api.informacion_basica.control_bom import _big_change_warning
    assert _big_change_warning(146, 158)          # Excel de otro modelo
    assert _big_change_warning(3, 158) is None    # ECO normal
    assert _big_change_warning(0, 0) is None


if __name__ == '__main__':
    test_eco_diff_no_marca_cambios_fantasma()
    test_eco_path_keys_sobrevive_renumeracion_del_erp()
