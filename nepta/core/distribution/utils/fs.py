import os
import logging
import shutil
import re

from nepta.core.distribution.command import Command

logger = logging.getLogger(__name__)


class Fs(object):
    DEBUGGING_PREFIX = None

    # Ref.: https://code.activestate.com/recipes/577257-slugify-make-a-string-usable-in-a-url-or-filename/
    @staticmethod
    def slugify(value):
        """
        Normalizes string, converts to lowercase, removes non-alpha characters,
        and converts spaces to hyphens.

        From Django's "django/template/defaultfilters.py".
        """
        _slugify_strip_re = re.compile(r"[^\w\s-]")
        _slugify_hyphenate_re = re.compile(r"[-\s]+")

        import unicodedata

        if not isinstance(value, str):
            value = str(value)

        value = unicodedata.normalize("NFKD", value)
        value = str(_slugify_strip_re.sub("", value).strip().lower())
        return _slugify_hyphenate_re.sub("-", value)

    @staticmethod
    def read(path):
        with open(path, "r") as fd:
            return fd.read()

    @staticmethod
    def write(path, content):
        with open(path, "w") as fd:
            fd.write(content)
            fd.flush()

    @staticmethod
    def append(path, content):
        with open(path, "a") as fd:
            fd.write(content)
            fd.flush()

    @classmethod
    def copy(cls, src, dst):
        logger.debug("copying file %s > %s", src, dst)
        shutil.copy(src, dst)
        cls.restore_path_context(dst)

    @staticmethod
    def rm(path):
        logger.debug("removing file :\t%s", path)
        os.remove(path)

    @staticmethod
    def mkdir(path):
        logger.debug("creating directory :\t %s", path)
        os.makedirs(path)

    @classmethod
    def copy_dir(cls, src, dst):
        logger.debug("copying directory %s > %s", src, dst)
        shutil.copytree(src, dst)
        cls.restore_path_context(dst)

    @staticmethod
    def rmdir(path):
        logger.debug("removing directory :\t%s", path)
        shutil.rmtree(path)

    @staticmethod
    def is_file(path):
        return os.path.isfile(path)

    @staticmethod
    def is_dir(path):
        return os.path.isdir(path)

    @staticmethod
    def path_exists(path):
        return os.path.exists(path)

    @staticmethod
    def list_path(path):
        return os.listdir(path)

    @classmethod
    def write_to_path(cls, path, content):
        dirname, _ = os.path.split(path)
        if not cls.path_exists(dirname):
            cls.mkdir(dirname)
        logger.debug("writing file name: %s\ncontent:\n%s", path, content)
        cls.write(path, content)
        cls.restore_path_context(path)

    @classmethod
    def append_to_path(cls, path, content):
        if not cls.path_exists(path):
            logger.debug("file %s does not exists, will create new one" % path)
            cls.write_to_path(path, content)
        else:
            already_contain = cls.read(path).find(content) >= 0
            if not already_contain:
                logger.debug("required content does not exists in file, appending")
                cls.append(path, content)
            else:
                logger.debug("required content is already in file. No action taken")

    @classmethod
    def copy_path(cls, src_path, dst_path):
        if not cls.path_exists(src_path):
            raise ValueError("path %s does not exists" % src_path)
        elif cls.is_file(src_path):
            cls.copy(src_path, dst_path)
        elif cls.is_dir(src_path):
            cls.copy_dir(src_path, dst_path)
        else:
            raise EnvironmentError

    @classmethod
    def rm_path(cls, path):
        if not cls.path_exists(path):
            raise ValueError("path %s does not exists" % path)
        elif cls.is_file(path):
            cls.rm(path)
        elif cls.is_dir(path):
            cls.rmdir(path)

    @staticmethod
    def chmod_path(path, mode=0o0755):
        logger.debug("chmodding path %s to %o", path, mode)
        os.chmod(path, mode)

    @staticmethod
    def restore_path_context(path):
        logger.debug("restoring security context : %s", path)
        c = Command("restorecon -FvvR %s" % path)
        c.run()
        c.wait()
