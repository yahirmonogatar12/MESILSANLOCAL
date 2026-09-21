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


if __name__ == '__main__':
    test_eco_diff_no_marca_cambios_fantasma()
    test_eco_path_keys_sobrevive_renumeracion_del_erp()
