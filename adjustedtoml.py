import toml
import tempfile
import os


class AdjustedToml:
    """
    AdjustedToml allows you to adjust a TOML file in a context manager.
    The original TOML file is adjusted and a new TOML file is created with the adjusted values.

    Example:
    with AdjustedToml("/path/to/config.toml", lambda x: x) as new_config_path:
        # do stuff with new_config_path
    """
    def __init__(self, original_conf_path, adjust, dir=None, delete=True, prefix=None):
        self.original_conf_path = original_conf_path
        self.adjust = adjust
        self.new_conf = None
        self.delete = delete
        self.prefix = prefix
        self.dir = dir

    def __enter__(self):
        with open(self.original_conf_path, "r") as f:
            self.original_conf = dict(toml.loads(f.read()))

        self.new_conf = self.adjust(self.original_conf.copy())

        with tempfile.NamedTemporaryFile(mode="w", delete=False, dir=self.dir, prefix=self.prefix) as f:
            f.write(toml.dumps(self.new_conf))
            self.new_conf = f.name

        return self.new_conf

    def __exit__(self, *_):
        if self.new_conf is not None and self.delete:
            os.remove(self.new_conf)


