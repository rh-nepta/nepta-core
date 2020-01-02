import urllib.request
import logging
import os

from nepta.core.strategies.generic import Strategy
from nepta.core.distribution import components
from nepta.core.distribution.command import Command
from nepta.core.model import attachments

from nepta.dataformat import AttachmentTypes

logger = logging.getLogger(__name__)


class SaveAttachments(Strategy):

    def __init__(self, conf, package):
        super().__init__()
        self.conf = conf
        self.package = package

    @Strategy.schedule
    def save_attachments(self):
        for attach in self.conf.get_subset(attachments.GenericAttachment):
            try:
                if isinstance(attach, attachments.Url):
                    url_response = urllib.request.urlopen(attach.url)
                    url_content = url_response.read().decode('ISO-8859-1')
                    url_attachment = self.package.attachments.new(AttachmentTypes.URL, attach.url, attach.alias)
                    url_attachment.path.write(url_content)

                if isinstance(attach, attachments.Directory):
                    dir_attachment = self.package.attachments.new(
                        AttachmentTypes.DIRECTORY, attach.d_path, attach.alias)
                    components.fs.copy_dir(attach.d_path, os.path.join(self.package.path, str(dir_attachment.path)))

                if isinstance(attach, attachments.File):
                    file_attachment = self.package.attachments.new(
                        AttachmentTypes.FILE, attach.f_path, attach.alias)
                    components.fs.copy(attach.f_path, os.path.join(self.package.path, str(file_attachment.path)))

                if isinstance(attach, attachments.CycleCommand):
                    item_list_cmd = Command(attach.cmd_for_list)
                    item_list_cmd.run()
                    item_list = [x.strip() for x in item_list_cmd.watch_output()[0].split()]

                    for item in item_list:
                        log_cmd_str = attach.cmdline.format(item)
                        log_cmd = Command(log_cmd_str)
                        log_cmd.run()
                        cmd_attachment = self.package.attachments.new(AttachmentTypes.COMMAND, log_cmd_str)
                        cmd_attachment.path.write(log_cmd.watch_output()[0])

                if isinstance(attach, attachments.Command):
                    c = Command(attach.cmdline)
                    c.run()
                    output, retcode = c.watch_output()
                    command_attachment = self.package.attachments.new(
                        AttachmentTypes.COMMAND, attach.cmdline, attach.alias)
                    command_attachment.path.write(output)

            except Exception as e:
                logger.error(f"Exception occur during execution of attachment {attach}. >>> Error: {e}")
