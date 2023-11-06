from textwrap import wrap


def convert_temp_from_hex(message: str, start_num: int, finish_num: int) -> float:
    """
    convert hex byte value to float number

    :param message: byte array str
    :param start_num: start index of array
    :param finish_num: end index of array
    :rtype: object converted number
    """
    hex_number = message.split("\n")[start_num:finish_num]
    hex_number = hex_number[::-1]
    dex_number = int("".join(hex_number), 16)

    return float(dex_number / 100)


def convert_temp_to_hex(number: float) -> str:
    """

    :param number: number to convert to hex
    :rtype: return string with formatted hex value
    """
    dex_number = int(number * 100)
    hex_number = hex(dex_number)[2:]  # delete 'ox' part
    # output value should be 8 char. so we should add '0' to the beginning of str
    add_len = 8 - len(hex_number)
    for i in range(add_len):
        hex_number = "0" + hex_number
    hex_arr = wrap(hex_number, 2)
    hex_arr.reverse()

    return "\n".join(hex_arr)
