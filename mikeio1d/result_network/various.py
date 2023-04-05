import re


def make_proper_variable_name(string, extra_string_before_digit='_'):
    """
    Makes a more proper variable name.
    """
    # Replace a dot, a minus, a left parentheses, a right parentheses, and a space by an underscore.
    string = re.sub(r'[.\-()\s+]', '_', string)
    # Replace more than two underscores with a single underscore.
    string = re.sub(r'_{2,}', '_', string)
    # Remove all non alpha numeric characters except for underscore.
    string = re.sub(r'[^a-zA-Z0-9_]', '', string)
    # Add an extra string is the string starts with a number.
    string = extra_string_before_digit + string if string and string[0].isdigit() else string
    # Remove a trailing underscore
    string = string[:-1] if string[-1] == '_' else string
    return string
