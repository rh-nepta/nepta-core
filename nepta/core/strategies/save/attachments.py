import urllib.request
import logging
import os

from nepta.core.strategies.generic import Strategy
from nepta.core.distribution import components
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
        for attach in self.conf.get_subset(attachments.Attachment):
            try:
                if isinstance(attach, attachments.Url):
                    url_response = urllib.request.urlopen(attach.url)
                    url_content = url_response.read().decode('ISO-8859-1')
                    url_attachment = self.package.attachments.new(AttachmentTypes.URL, attach.url)
                    url_attachment.path.write(url_content)

                if isinstance(attach, attachments.Directory):
                    dir_attachment = self.package.attachments.new(AttachmentTypes.DIRECTORY, attach.d_path)
                    components.fs.copy_dir(attach.d_path, os.path.join(self.package.path, str(dir_attachment.path)))

                if isinstance(attach, attachments.File):
                    file_attachment = self.package.attachments.new(AttachmentTypes.FILE, attach.f_path)
                    components.fs.copy(attach.f_path, os.path.join(self.package.path, str(file_attachment.path)))

                if isinstance(attach, attachments.CycleCommand):
                    item_list_cmd = components.Command(attach.cmd_for_list)
                    item_list_cmd.run()
                    item_list = [x.strip() for x in item_list_cmd.watch_output()[0].split()]

                    for item in item_list:
                        log_cmd_str = attach.cmdline.format(item)
                        log_cmd = components.Command(log_cmd_str)
                        log_cmd.run()
                        cmd_attachment = self.package.attachments.new(AttachmentTypes.COMMAND, log_cmd_str)
                        cmd_attachment.path.write(log_cmd.watch_output()[0])

                if isinstance(attach, attachments.Command):
                    c = components.Command(attach.cmdline)
                    c.run()
                    output, retcode = c.watch_output()
                    command_attachment = self.package.attachments.new(AttachmentTypes.COMMAND, attach.cmdline)
                    command_attachment.path.write(output)

            except Exception as e:
                logger.error("Exception occur during execution of attachment {}. "
                             ">>> Error: {}".format(attach, e))
