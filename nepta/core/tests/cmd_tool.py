from nepta.core.distribution.command import Command


class CommandToolException(Exception):
    """
    General exception of this package.
    """

    pass


class MissingRequiredArgument(CommandToolException):
    """
    Exception is raised when required argument is missing.
    """

    pass


class CommandArgument(object):
    def __init__(self, class_name, argument_name, required=False, argument_type=str, default_value=None):
        """
        This object is abstract class to program argument. It basically store tuple of argument
        information about argument, so it gives some semantics control to tuple.
        :param class_name: name, which is used in CommandTool as object attribute. -> "host"
        :param argument_name: name of program argument, which will be written into CLI -> "--host"
        :param argument_type: data type of argument, if True/False it means only the arguemnt is or is not there
        :param default_value: default value of argument
        """
        self.class_name = class_name
        self.argument_name = argument_name
        self.required = required
        self.argument_type = argument_type
        self.default_value = default_value


class CommandTool(object):

    PROGRAM_NAME = ''
    MAPPING = []

    def __init__(self, **kwargs):
        super().__init__()

        self._init_class_attr()  # set object attributes from MAPPING
        self.__dict__.update(kwargs)  # update object attributes with constructor arguments

        self._cmd = None
        self._exit_code = None
        self._output = None

    def __str__(self):
        def str_mapping():
            """
            Nicely format object attributes when printing to stdout
            :return: str
            """
            ret_str = ''
            for arg in self.MAPPING:
                ret_str += '\t{} {}\n'.format(arg.class_name, self.__dict__[arg.class_name])
            return ret_str

        return '{}\n{}'.format(self.PROGRAM_NAME, str_mapping())

    def __call__(self):
        self.run()

    def _init_class_attr(self):
        """
        Create object attributes for each argument defined in MAPPING.
        """
        for arg in self.MAPPING:
            self.__dict__[arg.class_name] = arg.default_value

    def _make_cli_args(self, args):
        """
        Create arguments for program from arguments list. There might be more argument lists, so this method is generic
        for each list.
        :param args: arguments list
        :return: formated string of attributes
        """
        ret_str = ''
        for arg in args:
            arg_value = self.__dict__[arg.class_name]
            if arg_value is not None:
                if arg.argument_type == bool:  # True/False argument
                    ret_str += ' {}'.format(arg.argument_name)
                else:  # key value argument
                    ret_str += ' {} {}'.format(arg.argument_name, arg_value)

            elif arg.required:  # if required and not set-> error
                raise MissingRequiredArgument(
                    'Argument {} is required in {} command.'.format(arg.argument_name, self.PROGRAM_NAME)
                )

        return ret_str

    def _make_cmd(self):
        """
        Create Command object from name of program and local attributes
        :return: Command object
        """
        return self.PROGRAM_NAME + self._make_cli_args(self.MAPPING)

    def run(self):
        """
        Execute current command.
        """
        self._cmd = Command(self._make_cmd())
        self._cmd.run()

    def watch_output(self):
        """
        Wait for end of program and return stdout of process.
        :return: stdout, exit code
        """
        if self._output is None and self._exit_code is None:
            self._output, self._exit_code = self._cmd.watch_output()
        return self._output, self._exit_code

    def clone(self):
        """
        Create a duplicate of current object and delete reference to running process.
        :return: object clone
        """
        cloned = self.__class__(**self.__dict__)
        cloned._cmd, cloned._exit_code, cloned._output = None, None, None
        return cloned

    def success(self):
        """
        Check if program execution was OK.
        :return: True if success else False
        """
        return self._exit_code == 0

    def clear(self):
        """
        Kill process and delete reference to Command obj
        """
        self._cmd.terminate()
        self._cmd, self._exit_code, self._output = None, None, None
