class Attachment(object):
    def __str__(self):
        return f'{self.__class__.__name__} attachments: {self.__dict__}'


class File(Attachment):
    def __init__(self, file_path):
        self.f_path = file_path


class Directory(Attachment):
    def __init__(self, directory_path):
        self.d_path = directory_path


class Command(Attachment):
    def __init__(self, cmdline):
        self.cmdline = cmdline


class CycleCommand(Command):
    def __init__(self, cmd_for_list, cmdline):
        super().__init__(cmdline)
        self.cmd_for_list = cmd_for_list

    def __str__(self):
        return f'{self.__class__.__name__}\n' \
               f'\tlist generator: {self.cmd_for_list}\n' \
               f'\tcommand: {self.cmdline}'


class Url(Attachment):
    def __init__(self, url):
        self.url = url
