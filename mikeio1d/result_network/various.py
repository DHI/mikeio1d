import re


def make_proper_variable_name(string, extra_string_before_digit='_'):
    """
    Makes a more proper variable name.

    It is assumed that the input string never is or after manipulations
    becomes an '_' or an empty string.
    """
    # Replace all non alpha numeric characters by an underscore.
    string = re.sub(r'[^a-zA-Z0-9]', '_', string)
    # Replace more than two underscores with a single underscore.
    string = re.sub(r'_{2,}', '_', string)
    # Add an extra string is the string starts with a number.
    string = extra_string_before_digit + string if string and string[0].isdigit() else string
    # Remove a starting underscore
    string = string[1:] if string[0] == '_' else string
    # Remove a trailing underscore
    string = string[:-1] if string[-1] == '_' else string
    return string
