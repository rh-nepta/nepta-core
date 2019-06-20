from nepta.core import distribution


class Attachment(object):
    def __init__(self, output_path):
        pass


class File(Attachment):
    def __init__(self, f_path, output_path=None):
        super(File, self).__init__(distribution.components.Fs.slugify(f_path))
        self.f_path = f_path

    def __str__(self):
        return 'File attachment: %s' % (self.f_path)
    
class Directory(Attachment):
    def __init__(self, f_path, output_path=None):
        super(Directory, self).__init__(distribution.components.Fs.slugify(f_path))
        self.d_path = f_path

    def __str__(self):
        return 'Directory attachment: %s' % (self.d_path)


class Command(Attachment):
    def __init__(self, cmdline, output_path=None):
        super(Command, self).__init__(output_path)
        self.cmdline = cmdline

    def __str__(self):
        return 'Command attachment: %s' % (self.cmdline)


class CycleCommand(Command):
    def __init__(self, cmd_for_list, cmdline, output_path=None):
        super().__init__(cmdline, output_path)
        self.cmd_for_list = cmd_for_list

    def __str__(self):
        return "%s attachment\n\tlist generator: %s \n\tcommand: %s" % (self.__class__.__name__, self.cmd_for_list, self.cmdline)


class Url(Attachment):
    def __init__(self, url, output_path=None):
        super(Url, self).__init__(output_path)
        self.url = url

    def __str__(self):
        return 'Url attachment: %s ' % (self.url)
