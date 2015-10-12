from twisted.internet import defer

class Semaphore:
    """A semaphore for event driven systems."""

    def __init__(self, tokens):
        self.waiting = []
        self.tokens  = tokens
        self.limit   = tokens

    def is_locked(self):
        return (bool)(not self.tokens)
    
    def acquire(self):
        """Attempt to acquire the token.

        @return Deferred which returns on token acquisition.
        """
        assert self.tokens >= 0
        d = defer.Deferred()
        if not self.tokens:
            self.waiting.append(d)
        else:
            self.tokens = self.tokens - 1
            d.callback(self)
        return d

    def release(self):
        """Release the token.

        Should be called by whoever did the acquire() when the shared
        resource is free.
        """
        assert self.tokens < self.limit
        self.tokens = self.tokens + 1
        if self.waiting:
            # someone is waiting to acquire token
            self.tokens = self.tokens - 1
            d = self.waiting.pop(0)
            d.callback(self)

    def _releaseAndReturn(self, r):
        self.release()
        return r

    def run(self, f, *args, **kwargs):
        """Acquire token, run function, release token.

        @return Deferred of function result.
        """
        d = self.acquire()
        d.addCallback(lambda r: defer.maybeDeferred(f, *args,
            **kwargs).addBoth(self._releaseAndReturn))
        return d
