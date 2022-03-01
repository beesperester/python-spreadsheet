import math


def format_color_red(string):
    return "\033[91m{}\033[00m".format(string)


def format_color_green(string):
    return "\033[92m{}\033[00m".format(string)


def format_color_yellow(string):
    return "\033[93m{}\033[00m".format(string)


def format_color_light_purple(string):
    return "\033[94m{}\033[00m".format(string)


def format_color_purple(string):
    return "\033[95m{}\033[00m".format(string)


def format_color_cyan(string):
    return "\033[96m{}\033[00m".format(string)


def format_color_light_gray(string):
    return "\033[97m{}\033[00m".format(string)


def format_color_black(string):
    return "\033[98m{}\033[00m".format(string)


def format_align(string: str, width: int, alignment: str = "left") -> str:
    alignment_padding = " " * max(width - len(string), 0)

    if alignment == "left":
        return string + alignment_padding
    elif alignment == "right":
        return alignment_padding + string
    elif alignment == "center":
        center_alignment_padding = " " * int(math.floor(len(alignment_padding) / 2.0))

        return (
            center_alignment_padding
            + string
            + center_alignment_padding
            + (
                " "
                * max(
                    len(alignment_padding) - len(center_alignment_padding) * 2,
                    0,
                )
            )
        )

    return string
