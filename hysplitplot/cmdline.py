# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# cmdline.py
#
# Holder for command-line arguments.
# ---------------------------------------------------------------------------

import logging

from hysplitplot import util


logger = logging.getLogger(__name__)


class CommandLineArguments:
    """A simple command-line arguments holder

    Provides access to parsed option values.
    """

    def __init__(self, args=None):
        """Constructor

        :param args: list of command-line arguments excluding the program name.
        """
        self.args = dict()
        self.unprocessed_args = []
        self.ignore_arg_stopper = True  # ignore -:
        if args is not None:
            self.add(args)

    def clear(self):
        """Removes all arguments.

        """
        self.args.clear()

    def add(self, args):
        """Parses and adds command-line arguments.

        :param args: list of command-line arguments excluding the program name.
        """
        for arg in args:
            if len(arg) >= 2:
                if arg == "-:":
                    if not self.ignore_arg_stopper:
                        break
                elif arg[0:2] == "--":
                    if arg.count("=") > 0:
                        k = arg.index("=")
                        opt = arg[:k]
                        val = arg[k+1:]
                        self.args[opt] = val
                    else:
                        opt = arg
                        val = None
                        self.args[opt] = val
                    logger.debug("adding command-line argument %s as %s -> %s",
                                 arg, opt, val)
                elif arg[0] == "+" or arg[0] == "-":
                    opt = arg[:2]
                    val = arg[2:]
                    self.args[opt] = val
                    logger.debug("adding command-line argument %s as %s -> %s",
                                 arg, opt, val)
                else:
                    self.unprocessed_args.append(arg)
            else:
                self.unprocessed_args.append(arg)

    def has_arg(self, option):
        if isinstance(option, list):
            for opt in option:
                if opt in self.args:
                    return True
            return False
        else:
            return True if (option in self.args) else False

    def get_value(self, option):
        """Returns an option value.

        :param option: name of an option, e.g., -a.
        :return: None if the option is not found. Otherwise, the option
                 value as string.
        """
        if isinstance(option, list):
            for opt in option:
                if opt in self.args:
                    return self.args[opt]
            return None
        else:
            return self.args[option] if (option in self.args) else None

    def get_string_value(self, option, default_value):
        """Returns an option value as string.

        :param option: name of an option.
        :param default_value: value to be returned if the option is not found.
        :return: a string.
        """
        val = self.get_value(option)
        return default_value if (val is None or (not val)) else val

    def get_integer_value(self, option, default_value):
        """Returns an option value as integer.

        :param option: name of an option.
        :param default_value: value to be returned if the option is not found.
        :return: an integer.
        """
        val = self.get_value(option)
        if (val is None or (not val)):
            return default_value
        else:
            try:
                return int(val)
            except ValueError:
                logger.error("ignored non-integer value %s for command-line "
                             "option %s", val, option)
                return default_value

    def get_float_value(self, option, default_value):
        """Returns an option value as floating-point number.

        :param option: name of an option.
        :param default_value: value to be returned if the option is not found.
        :return: a floating-point number.
        """
        val = self.get_value(option)
        if (val is None or (not val)):
            return default_value
        else:
            try:
                return float(val)
            except ValueError:
                logger.error("ignored non-float value %s for command-line "
                             "option %s", val, option)
                return default_value

    def get_boolean_value(self, option, default_value):
        """Returns an option value as boolean.

        The option value is first converted to an integer. If the integer is
        equal to or less than 0, False is returned.  Otherwise, True is
        returned.

        :param option: name of an option.
        :param default_value: value to be returned if the option is not found.
        :return: an integer.
        """
        val = self.get_value(option)
        if (val is None or (not val)):
            return default_value
        else:
            try:
                return util.convert_int_to_bool(val)
            except ValueError:
                logger.error("ignored non-boolean value %s for command-line "
                             "option %s", val, option)
                return default_value
