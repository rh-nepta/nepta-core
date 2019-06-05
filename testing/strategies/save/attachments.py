import urllib.request
import logging

from testing.strategies.generic import Strategy
from testing.distribution import components
from testing.model import attachments

logger = logging.getLogger(__name__)


class SaveAttachments(Strategy):

    def __init__(self, conf, package):
        super().__init__()
        self.conf = conf
        self.package = package

    @Strategy.schedule
    def save_attachments(self):
        for attach in self.conf.get_subset(attachments.Attachment):
            try:
                if isinstance(attach, attachments.Url):
                    url_response = urllib.request.urlopen(attach.url)
                    url_content = url_response.read().decode('ISO-8859-1')
                    url_attachment = self.package.attachments.new.url(attach.url)
                    url_attachment.path.write(url_content)
                if isinstance(attach, attachments.Directory):
                    dir_attachment = self.package.attachments.new.directory(attach.d_path)
                    components.fs.rm_path(str(dir_attachment.path))
                    components.fs.copy_dir(attach.d_path, str(dir_attachment.path))
                if isinstance(attach, attachments.File):
                    file_attachment = self.package.attachments.new.file(attach.f_path)
                    components.fs.copy(attach.f_path, str(file_attachment.path))
                if isinstance(attach, attachments.CycleCommand):
                    item_list_cmd = components.Command(attach.cmd_for_list)
                    item_list_cmd.run()
                    item_list = [x.strip() for x in item_list_cmd.watch_output()[0].split()]

                    for item in item_list:
                        log_cmd_str = attach.cmdline.format(item)
                        log_cmd = components.Command(log_cmd_str)
                        log_cmd.run()
                        cmd_attachment = self.package.attachments.new.command(log_cmd_str)
                        cmd_attachment.path.write(log_cmd.watch_output()[0])

                if isinstance(attach, attachments.Command):
                    c = components.Command(attach.cmdline)
                    c.run()
                    output, retcode = c.watch_output()
                    command_attachment = self.package.attachments.new.command(attach.cmdline)
                    command_attachment.path.write(output)
            except Exception as e:
                logger.error("Exception occur during execution of attachment {}. "
                             ">>> Error: {}".format(attach, e))
