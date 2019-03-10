from collections import OrderedDict

from dataclasses import dataclass
from marshmallow import fields, Schema, ValidationError
from typing import Callable, Dict
import inspect

empty = inspect.Signature.empty


@dataclass
class Arg:
    name: str
    type: type
    default: any


@dataclass
class Spec:
    args: Dict[str, Arg]
    return_type: type
    has_args: bool = False
    has_kwargs: bool = False

    @classmethod
    def get(cls, fn: Callable):
        signature = inspect.signature(fn)
        has_args = False
        has_kwargs = False
        args = []

        for name, param in signature.parameters.items():
            if param.kind == param.VAR_POSITIONAL:
                has_args = True
            elif param.kind == param.VAR_KEYWORD:
                has_kwargs = True
            else:
                args.append((name, Arg(name=name, type=param.annotation, default=param.default)))

        return cls(
            args=OrderedDict(args),
            return_type=signature.return_annotation,
            has_args=has_args,
            has_kwargs=has_kwargs,
        )


def load_value(value, arg_type):
    if not arg_type or arg_type is empty:
        return value

    load_with_marshmallow = _get_method(arg_type, Schema, 'load') or _get_method(arg_type, fields.Field, 'deserialize')

    if load_with_marshmallow:
        value = load_with_marshmallow(value)
    elif callable(arg_type):
        try:
            value = arg_type(value)
        except (TypeError, ValueError) as e:
            raise ValidationError(e) from e

    return value


def _get_method(arg_type, kls, method):
    if isinstance(arg_type, kls):
        meth = getattr(arg_type, method)
    elif inspect.isclass(arg_type) and issubclass(arg_type, Schema):
        meth = getattr(arg_type(), method)
    else:
        meth = None

    return meth
