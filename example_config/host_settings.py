from nepta.core import model
from nepta.core.model import attachments
from nepta.core.model.system import Package as Pckg

host_settings = model.bundles.Bundle()

host_settings.packages.vim = Pckg('vim')
host_settings.packages.tmux = Pckg('tmux')

host_settings.attachments.cmd.ip_a = attachments.Command('ip a')
host_settings.attachments.cmd.lscpu = attachments.Command('lscpu')
host_settings.attachments.dir.log = attachments.Directory('/var/log')
