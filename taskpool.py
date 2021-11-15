from concurrent.futures import ThreadPoolExecutor

class TaskPool(ThreadPoolExecutor):
    """
    A wrapper around ThreadPoolExecutor that keeps track of submissions
    so they can be waited on, and also provides a delayed start() method
    """
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.submissions = []

    def submit(self, func, *args, **kwargs):
        submission = super().submit(func, *args, **kwargs)
        self.submissions.append(submission)
        return submission 

    def wait(self):
        for submission in self.submissions:
            submission.result()
