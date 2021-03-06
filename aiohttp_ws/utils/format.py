import re
from functools import partial

UNDERSCORE = (re.compile('(.)([A-Z][a-z]+)'), re.compile('([a-z0-9])([A-Z])'))


def underscore_text(text: str):
    """Converts text that may be camelcased into an underscored format"""
    return UNDERSCORE[1].sub(r'\1_\2', UNDERSCORE[0].sub(r'\1_\2', text)).lower()


def camelcase_text(text: str):
    """Converts text that may be underscored into a camelcase format"""
    return text[0] + "".join(text.title().split('_'))[1:]


def _transform(content, transformator):
    if isinstance(content, dict):
        new_dictionary = {}
        for key, value in content.items():
            if isinstance(key, str):
                key = transformator(key)
            new_dictionary[key] = _transform(value, transformator)
        return new_dictionary
    elif isinstance(content, list):
        new_list = []
        for element in content:
            new_list.append(_transform(element, transformator))
        return new_list
    else:
        return content


camelcase = partial(_transform, transformator=camelcase_text)
underscore = partial(_transform, transformator=underscore_text)
