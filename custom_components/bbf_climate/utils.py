def convert_temp_from_dex(message: str, start_num: int, finish_num: int) -> float:
    """
    convert hex byte value to float number

    :param message: byte array str
    :param start_num: start index of array
    :param finish_num: end index of array
    :rtype: object converted number
    """
    hex_number = message.split("\n")[start_num:finish_num]
    hex_number = hex_number[::-1]
    dex_number = int("".join(hex_number))

    return float(dex_number/100)
