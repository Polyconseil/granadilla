"""Trivial vcard generator."""

import re


class Field(object):
    SINGLE = 1
    MULTI = 2
    MULTI_NESTED = 3

    def __init__(self, prefix, subtype='', cardinality=SINGLE):
        self.prefix = prefix
        self.subtype = subtype
        self.cardinality = cardinality

    def _escape_one(self, value):
        value = re.sub(r'([,;\\])', r'\\\1', value)
        value = value.replace('\n', '\\n')
        return value

    def _escape(self, value):
        if self.cardinality == self.SINGLE:
            return self._escape_one(value)
        elif self.cardinality == self.MULTI:
            return ';'.join(self._escape_one(v) for v in value)
        else:
            assert self.cardinality == self.MULTI_NESTED
            return ';'.join(
                ','.join(self._escape_one(subv) for subv in v)
                for v in value
            )

    def filled(self, value):
        if self.cardinality == self.SINGLE:
            return bool(value)
        elif self.cardinality == self.MULTI:
            return any(v for v in value)
        else:
            assert self.cardinality == self.MULTI_NESTED
            return any(any(subv for subv in v) for v in value)

    def render(self, value):
        if self.subtype:
            subtype_txt = ';TYPE=%s' % self.subtype
        else:
            subtype_txt = ''
        return '%s%s:%s' % (self.prefix, subtype_txt, self._escape(value))


class VCard(object):

    ALL_FIELDS = {
        'src': Field('SOURCE'),
        'kind': Field('KIND'),
        'email': Field('EMAIL', subtype='INTERNET'),
        'full_name': Field('FN'),
        'names': Field('N', cardinality=Field.MULTI_NESTED),
        'cell': Field('TEL', subtype='CELL'),
        'phone': Field('TEL', subtype='VOICE'),
        'org': Field('ORG', cardinality=Field.MULTI_NESTED),
        'photo': Field('PHOTO'),
    }

    def __init__(self):
        self.data = {}

    def __getitemm__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        assert key in self.ALL_FIELDS
        self.data[key] = value

    def render_bytes(self):
        inner_lines = []
        for key, field in self.ALL_FIELDS.items():
            if key not in self.data:
                continue
            value = self.data[key]
            if not field.filled(value):
                continue
            inner_lines.append(field.render(value))

        lines = [
            'BEGIN:VCARD',
            'VERSION:3.0',
        ] + sorted(inner_lines) + [
            'END:VCARD',
        ]
        return '\r\n'.join(lines).encode('utf-8')
