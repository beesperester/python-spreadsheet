from __future__ import annotations
from ctypes import alignment

import math
import string

from collections.abc import MutableMapping
from enum import Enum
from typing import Callable, Iterator, List, Optional, Tuple, Type, Union, Generator

from spreadsheet.format import format_align, format_color_red


T_cell_value = Union[str, float, int, None, Callable[["Cell"], Union[str, float, int]]]
T_cell_final_value = Union[str, float, int, None]
T_spreadsheet_value = Union[str, float, int, "Cell"]

T_format_value = Callable[[T_cell_value], str]
T_render_value = Callable[["Cell", str], str]


class Alignment:

    LEFT: str = "left"
    CENTER: str = "center"
    RIGHT: str = "right"


def format_noop(value: T_cell_value) -> str:
    if value is None:
        return ""

    return str(value)


def render_noop(raw_value: Cell, value: str) -> str:
    return value


class Cell:

    _value: T_cell_value
    spreadsheet: Spreadsheet
    format_fn: T_format_value
    render_fn: T_render_value
    alignment: str

    @property
    def value(self) -> T_cell_final_value:
        if isinstance(self._value, (str, float, int)):
            return self._value
        elif callable(self._value):
            return self._value(self)

        return self._value

    def __init__(
        self,
        value: T_cell_value,
        spreadsheet: Spreadsheet,
        format_fn: Optional[T_format_value] = None,
        render_fn: Optional[T_render_value] = None,
        alignment: Optional[str] = None,
    ) -> None:
        if format_fn is None:
            format_fn = format_noop

        if render_fn is None:
            render_fn = render_noop

        if alignment is None:
            alignment = Alignment.LEFT

        self._value = value
        self.spreadsheet = spreadsheet
        self.format_fn = format_fn
        self.render_fn = render_fn
        self.alignment = alignment

    def __repr__(self) -> str:
        return f"Cell(value={repr(self.value)})"

    def __str__(self) -> str:
        return self.format_fn(self.value)

    def render(self) -> str:
        return self.render_fn(self, str(self))

    def get_cell_id(self) -> str:
        return self.spreadsheet.get_cell_id(self)

    def get_position(self) -> Tuple[int, int]:
        return position_from_cell_id(self.get_cell_id())

    def get_relative_neighbour(self, offset: Tuple[int, int]) -> Cell:
        x, y = self.get_position()

        x += offset[0]
        y += offset[1]

        return self.spreadsheet.get_cell_at_position((x, y))


def column_id_from_number(id: int) -> str:
    string_id: str = ""

    while id > 0:
        id, remainder = divmod(id - 1, len(string.ascii_uppercase))

        string_id = string.ascii_uppercase[remainder] + string_id

    return string_id


def number_from_column_id(column_id: str) -> int:
    num = 0

    for c in column_id:
        if c in string.ascii_uppercase:
            num = num * len(string.ascii_uppercase) + (ord(c.upper()) - ord("A")) + 1

    return num


def row_number_from_cell_id(cell_id: str) -> int:
    return int(cell_id.split("_")[0])


def column_number_from_cell_id(cell_id: str) -> int:
    return number_from_column_id(cell_id.split("_")[1])


def position_from_cell_id(cell_id: str) -> Tuple[int, int]:
    return (row_number_from_cell_id(cell_id), column_number_from_cell_id(cell_id))


def cell_id_from_position(position: Tuple[int, int]) -> str:
    return format_cell_id(position[0], column_id_from_number(position[1]))


def column_ids_from_number(length: int) -> Generator:
    for id in range(length):
        yield column_id_from_number(id)


def format_cell_id(row_id: int, column_id: str) -> str:
    return f"{row_id}_{column_id}"


def format_seconds_timecode(seconds: int, precision: str = "minutes") -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)

    if precision == "minutes":
        return "{:02d}:{:02d}".format(int(h), int(m))
    elif precision == "hours":
        return "{:02d}".format(int(h))

    return "{:02d}:{:02d}:{:02d}".format(int(h), int(m), int(s))


def format_seconds(seconds: T_cell_value) -> str:
    if isinstance(seconds, int):
        return format_seconds_timecode(seconds, precision="minutes")

    return str(seconds)


T_position = Tuple[int, int]
T_bounds = Tuple[T_position, T_position]


class Selection:

    bounds: List[T_bounds]

    def __init__(
        self,
        start: Optional[T_position] = None,
        stop: Optional[T_position] = None,
        bounds: Optional[List[T_bounds]] = None,
    ) -> None:
        self.bounds = []

        if start and stop:
            self.bounds = [(start, stop)]

        if bounds:
            self.bounds = bounds

    def __add__(self, other: Selection) -> Selection:
        return Selection(bounds=[] + self.bounds + other.bounds)


class Spreadsheet(MutableMapping):

    cells: dict[str, Cell]

    def __init__(self) -> None:
        self.cells = {}

    def __setitem__(self, cell_id: str, cell: Cell) -> None:
        self.cells[cell_id] = cell

    def __getitem__(self, cell_id: str) -> Cell:
        return self.cells.get(cell_id, Cell(None, self))

    def __delitem__(self, cell_id: str) -> None:
        del self.cells[cell_id]

    def __iter__(self) -> Iterator[str]:
        return iter(self.cells)

    def __len__(self) -> int:
        return len(self.cells)

    def fill(self, data: list[list[T_spreadsheet_value]]) -> None:
        for row_id, row in enumerate(data):
            for column_id, value in zip(column_ids_from_number(len(row)), row):
                cell_id = format_cell_id(row_id, column_id)

                self.cells[cell_id] = (
                    value if isinstance(value, Cell) else Cell(value, self)
                )

    def get_num_rows(self) -> int:
        return max([row_number_from_cell_id(x) for x in self.cells.keys()]) + 1

    def get_num_columns(self) -> int:
        return max([column_number_from_cell_id(x) for x in self.cells.keys()]) + 1

    def get_shape(self) -> Tuple[int, int]:
        return (self.get_num_rows(), self.get_num_columns())

    def get_columns(self) -> list[list[Cell]]:
        return [
            [
                self[format_cell_id(y, column_id_from_number(x))]
                for y in range(self.get_num_rows())
            ]
            for x in range(self.get_num_columns())
        ]

    def get_rows(self) -> list[list[Cell]]:
        return [
            [
                self[format_cell_id(y, column_id_from_number(x))]
                for x in range(self.get_num_columns())
            ]
            for y in range(self.get_num_rows())
        ]

    def get_column_widths(self) -> list[int]:
        return [max([len(str(x)) for x in column]) for column in self.get_columns()]

    def get_cell_id(self, cell: Cell) -> str:
        for cell_id, cell_instance in self.cells.items():
            if cell_instance is cell:
                return cell_id

        raise Exception(f"Unable to find cell {cell}")

    def get_cell_at_position(self, position: Tuple[int, int]) -> Cell:
        x, y = position

        if x < 0:
            raise Exception(f"Out of bounds for {x=}")

        if y < 0:
            raise Exception(f"Out of bounds for {y=}")

        return self[cell_id_from_position((x, y))]

    def get_cells(self, selection: Selection) -> set[Cell]:
        cells: set[Cell] = set()

        for start, stop in selection.bounds:
            start_row, start_column = start
            stop_row, stop_column = stop

            for row in range(start_row, stop_row):
                for column in range(start_column, stop_column):
                    cells.add(self.get_cell_at_position((row, column)))

        return cells

    def render(self, padding: int = 4) -> None:
        overall_padding = " " * padding

        for row in self.get_rows():
            line = ""

            for width, cell in zip(self.get_column_widths(), row):
                line += (
                    format_align(str(cell), width, cell.alignment).replace(
                        str(cell), cell.render()
                    )
                    + overall_padding
                )

            print(line)


def highlight(cell: Cell, value: str) -> str:
    frame_average_cell = cell.get_relative_neighbour((0, 1))

    if isinstance(frame_average_cell.value, int) and frame_average_cell.value > 40:
        return format_color_red(value)

    return value


def sum_row(cell: Cell) -> int:
    position = cell.get_position()

    start = (position[0], 1)
    stop = (position[0], position[1])

    cells = cell.spreadsheet.get_cells(Selection(start, stop))

    print(cells)

    return 0


if __name__ == "__main__":
    spreadsheet = Spreadsheet()
    spreadsheet.fill(
        [
            [
                "layer",
                Cell("frame average", spreadsheet, alignment=Alignment.RIGHT),
                Cell("range average", spreadsheet, alignment=Alignment.RIGHT),
                Cell("range last", spreadsheet, alignment=Alignment.RIGHT),
                Cell("version", spreadsheet, alignment=Alignment.RIGHT),
            ],
            [
                Cell("le2000", spreadsheet, render_fn=highlight),
                Cell(
                    60, spreadsheet, format_fn=format_seconds, alignment=Alignment.RIGHT
                ),
                Cell(
                    90, spreadsheet, format_fn=format_seconds, alignment=Alignment.RIGHT
                ),
                Cell(
                    70, spreadsheet, format_fn=format_seconds, alignment=Alignment.RIGHT
                ),
                Cell(1, spreadsheet, alignment=Alignment.RIGHT),
            ],
            ["", Cell(sum_row, spreadsheet, alignment=Alignment.RIGHT)],
        ]
    )

    print(spreadsheet.get_cells(Selection((0, 0), (1, 2))))

    # spreadsheet.render()

    # print(spreadsheet.get_shape())

    # print(generate_column_id(number_from_column_id("AAB")))
