from __future__ import annotations

import tkinter as tk
from typing import Any, Callable, Dict, Tuple, TypeVar

T = TypeVar('T')
class SelectableComboBox(tk.OptionMenu):

    def __init__(self, 
                 master: Any, 
                 values: Dict[str, Any],
                 initial_value: str,
                 variable: tk.Variable = None, 
                 onSelectCb: Callable[..., None] = None,
                 cb_args: Tuple=(),
                 cb_kwargs: Dict[str, Any] = {}) -> None:
        self.__strVar = tk.StringVar()
        self.__strVar.set(initial_value)
        super().__init__(
            master, 
            self.__strVar, 
            *values.keys(),
            command=self.__onChangeHandler)
        self.__variable = variable
        self.__onSelectCb = onSelectCb
        self.__values = values
        self.__cb_args = cb_args
        self.__cb_kwargs = cb_kwargs

    @property
    def currentValue(self) -> Any:
        display_value = self.__strVar.get()
        return_value = self.__values[display_value]
        return return_value

    def __onChangeHandler(self, value: tk.StringVar):
        display_value = self.__strVar.get()
        return_value = self.__values[display_value]
        if self.__variable:
            self.__variable.set(return_value)
        if self.__onSelectCb is not None:
            self.__onSelectCb(self, return_value, *self.__cb_args, **self.__cb_kwargs)