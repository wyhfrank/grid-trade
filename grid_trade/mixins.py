class FieldFormatMixin:
    # A new property of `NAME_s` will be added for each of the `NAME` variables
    fields_to_format = {}
    price_precision = 0
    amount_precision = 4

    @classmethod
    def set_precision(cls, price_precision, amount_precision):
        cls.price_precision = price_precision
        cls.amount_precision = amount_precision
        for field, setting in cls.fields_to_format.items():
            if setting.get('_type', '') == 'price':
                setting['precision'] = price_precision
            if setting.get('_type', '') == 'amount':
                setting['precision'] = amount_precision

    @classmethod
    def get_precision(cls, key, default=0):
        setting = cls.fields_to_format.get(key, {})
        return setting.get('precision', default)

    # @classmethod
    # def round_dict(cls, data: dict):
    #     for k, v in data.items():
    #         precision = cls.get_precision(key=k)
    #         data[k] = round(v, precision)
    #     return data

    @classmethod
    def round_obj(cls, obj):
        for key in cls.fields_to_format.keys():
            precision = cls.get_precision(key=key)
            val = getattr(obj, key)
            val = round(val, precision)
            try:
                setattr(obj, key, val)
            except AttributeError:
                pass
        return obj