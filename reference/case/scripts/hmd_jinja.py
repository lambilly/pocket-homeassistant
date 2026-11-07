# -*- coding: utf-8 -*-
"""共享：本地复刻 HA 模板环境（用于校验和预览渲染）。"""
import datetime
import json
import types

from jinja2 import Environment


class _User(types.SimpleNamespace):
    """模拟 HA websocket render_template 里的 user 对象（user.name 才是真名）。"""
    def __str__(self):
        return ''


def build_env(states_path='.workbuddy/ha_states.json', user='林宗华'):
    STATES = {e['entity_id']: e for e in json.load(open(states_path, encoding='utf-8'))}

    def _states(eid):
        return STATES.get(eid, {}).get('state', 'unknown')

    def _state_attr(eid, attr, default=None):
        v = (STATES.get(eid, {}).get('attributes') or {}).get(attr)
        return default if v is None else v

    def _is_state(eid, val):
        s = _states(eid)
        return s == val if isinstance(val, str) else s in val

    def _expand(*args):
        out = []
        for a in args:
            e = STATES.get(a)
            out.append({'entity_id': a, 'state': e['state'] if e else 'unknown'})
        return out

    def _as_ts(v, default=None):
        if v in (None, '', 'unknown', 'unavailable'):
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    def _ts_custom(value, fmt='%H:%M', local=True):
        if value in (None, ''):
            return ''
        return datetime.datetime.fromtimestamp(float(value)).strftime(fmt)

    def _num(v, d=0):
        try:
            return float(v)
        except (TypeError, ValueError):
            return d

    env = Environment(autoescape=False)
    env.globals.update(states=_states, state_attr=_state_attr, is_state=_is_state,
                       expand=_expand, user=_User(name=user), now=datetime.datetime.now,
                       as_timestamp=_as_ts, states_obj=STATES)
    env.filters.update(
        as_timestamp=_as_ts, timestamp_custom=_ts_custom,
        float=lambda v, d=0: _num(v, d),
        int=lambda v, d=0: int(_num(v, d)) if str(v).replace('.', '', 1).lstrip('-').isdigit() else d,
        round=lambda v, p=0: round(_num(v, v), p) if isinstance(v, (int, float)) or str(v).replace('.', '', 1).lstrip('-').isdigit() else v,
        relative_time=lambda v: str(v),
    )
    return env, STATES
