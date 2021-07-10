
class FieldFormatMixin:
    # A new property of `NAME_s` will be added for each of the `NAME` variables
    fields_to_format = {}

    @classmethod
    def set_precision(cls, price_precision, amount_precision):
        for field, setting in cls.fields_to_format.items():
            if setting.get('_type', '') == 'price':
                setting['precision'] = price_precision
            if setting.get('_type', '') == 'amount':
                setting['precision'] = amount_precision