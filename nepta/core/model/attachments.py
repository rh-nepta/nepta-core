from nepta.dataformat import Compression


class GenericAttachment(object):
    def __init__(self, alias=None, compression=Compression.NONE):
        self.alias = alias
        self.compression = compression

    def __str__(self):
        return f'{self.__class__.__name__} attachment: {self.__dict__}'


class File(GenericAttachment):
    def __init__(self, file_path, alias=None, compression=Compression.NONE):
        super().__init__(alias, compression)
        self.f_path = file_path


class Directory(GenericAttachment):
    def __init__(self, directory_path, alias=None, compression=Compression.NONE):
        super().__init__(alias, compression)
        self.d_path = directory_path


class Command(GenericAttachment):
    def __init__(self, cmdline, alias=None, compression=Compression.NONE):
        super().__init__(alias, compression)
        self.cmdline = cmdline


class CycleCommand(Command):
    def __init__(self, cmd_for_list, cmdline, alias=None, compression=Compression.NONE):
        super().__init__(cmdline, alias, compression)
        self.cmd_for_list = cmd_for_list

    def __str__(self):
        return f'{self.__class__.__name__}\n' f'\tlist generator: {self.cmd_for_list}\n' f'\tcommand: {self.cmdline}'


class Url(GenericAttachment):
    def __init__(self, url, alias=None, compression=None):
        super().__init__(alias, compression)
        self.url = url
