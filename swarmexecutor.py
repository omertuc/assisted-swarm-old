import os
import subprocess


class SwarmExecutor:
    def __init__(self, logging):
        self.logging = logging

    def log_cmd(self, *args, **kwargs):
        def dictionary_diff(a, b):
            return {k: v for k, v in a.items() if k not in b or v != b[k]}

        if "env" in kwargs:
            extra_env = dictionary_diff(kwargs["env"], os.environ)
            self.logging.info(f"Executing command: {args} with env {extra_env}")
        else:
            self.logging.info(f"Executing command: {args}")

    @staticmethod
    def prepare_sudo_command(command, env):
        return ["sudo", f"--preserve-env={','.join(env.keys())}"] + command

    def Popen(self, *args, **kwargs):
        self.log_cmd(*args, **kwargs)
        return subprocess.Popen(*args, **kwargs)

    def check_call(self, *args, **kwargs):
        self.log_cmd(*args, **kwargs)
        return subprocess.check_call(*args, **kwargs)

    def check_output(self, *args, **kwargs) -> bytes:
        self.log_cmd(*args, **kwargs)
        output = subprocess.check_output(*args, **kwargs)

        if type(output) is bytes:
            return output
        else:
            return output.encode('utf-8')
